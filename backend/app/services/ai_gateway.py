"""Provider adapters, encrypted configuration and organization-wide AI budgets."""
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app import database, models

DEFAULT_BASES = "https://api.groq.com/openai/v1,https://api.openai.com/v1,https://openrouter.ai/api/v1"


def estimated_reservation(body, max_output_tokens):
    """Approximate UTF-8 prompt tokens without treating every byte as a token."""
    request_bytes = len(json.dumps(body, ensure_ascii=False).encode())
    estimated_input_tokens = (request_bytes + 3) // 4
    return estimated_input_tokens + max_output_tokens + 256


def cipher():
    try:
        return Fernet(os.environ["SYS_AI_ENCRYPTION_KEY"].encode())
    except (KeyError, ValueError, TypeError):
        raise HTTPException(503, "AI credential encryption is not configured on the server")


def allowed_bases():
    return [v.strip().rstrip("/") for v in os.getenv("SYS_AI_ALLOWED_BASE_URLS", DEFAULT_BASES).split(",") if v.strip()]


def validate_base(protocol, base):
    base = base.rstrip("/")
    parsed = urlsplit(base)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(422, "Base URL must not contain credentials, query parameters or fragments")
    if protocol == "openai_compatible":
        if parsed.scheme != "https" or base not in allowed_bases():
            raise HTTPException(422, "Use an HTTPS base URL approved in SYS_AI_ALLOWED_BASE_URLS")
    elif protocol == "ollama":
        approved = os.getenv("SYS_AI_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        if base != approved or parsed.scheme not in {"http", "https"}:
            raise HTTPException(422, "Ollama URL must match the server-configured SYS_AI_OLLAMA_BASE_URL")
    return base


def get_config(db):
    return db.get(models.AIProviderSettings, 1)


def public_config(row):
    fields = ("label", "protocol", "base_url", "model", "enabled", "daily_requests", "daily_tokens",
              "minute_requests", "minute_tokens", "student_daily_requests", "max_output_tokens", "revision")
    data = {name: getattr(row, name) for name in fields} if row else {
        "label": "Groq pilot", "protocol": "openai_compatible", "base_url": "https://api.groq.com/openai/v1",
        "model": "", "enabled": False, "daily_requests": 100, "daily_tokens": 150000,
        "minute_requests": 4, "minute_tokens": 7000, "student_daily_requests": 2, "max_output_tokens": 1500, "revision": 0,
    }
    data["has_api_key"] = bool(row and row.encrypted_key)
    data["runtime_mode"] = (os.getenv("SYS_AI_PROVIDER") or "configured").strip().lower()
    data["approved_base_urls"] = allowed_bases()
    data["ollama_base_url"] = os.getenv("SYS_AI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        cipher(); data["encryption_ready"] = True
    except HTTPException:
        data["encryption_ready"] = False
    return data


def save_config(db, payload, actor):
    data = payload.model_dump(exclude={"api_key", "clear_api_key", "expected_revision"})
    data["base_url"] = validate_base(data["protocol"], data["base_url"])
    db.query(models.AIProviderSettings).filter_by(id=1).update({models.AIProviderSettings.revision: models.AIProviderSettings.revision}, synchronize_session=False)
    row = db.query(models.AIProviderSettings).filter_by(id=1).first()
    if payload.expected_revision != (row.revision if row else 0):
        raise HTTPException(409, "AI settings changed; reload before saving")
    if row is None:
        row = models.AIProviderSettings(id=1, revision=0)
        db.add(row)
    changed_destination = (row.base_url, row.protocol) != (data["base_url"], data["protocol"])
    if changed_destination or payload.clear_api_key:
        row.encrypted_key = None
    if payload.api_key is not None:
        secret = payload.api_key.get_secret_value().strip()
        if secret:
            row.encrypted_key = cipher().encrypt(secret.encode()).decode()
    if data["protocol"] == "openai_compatible" and data["enabled"] and not row.encrypted_key:
        raise HTTPException(422, "An API key is required before enabling this provider")
    for name, value in data.items():
        setattr(row, name, value)
    row.revision += 1
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action="ai.settings.updated", target_type="ai_provider", target_id=1,
        summary="AI provider configuration updated", details={"protocol": row.protocol, "model": row.model, "revision": row.revision,
        "credential_changed": bool(payload.api_key is not None or payload.clear_api_key or changed_destination)}))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "AI settings changed; reload before saving")
    db.refresh(row)
    return public_config(row)


def _request(config, secret, system, user, context, response_schema=None, schema_name="sys_response"):
    # Audit-only IDs are never sent to an external provider.
    academic = {k: v for k, v in (context or {}).items() if k not in {"actor_id", "session_id"}}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user + "\nAcademic context: " + json.dumps(academic, ensure_ascii=False)}]
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = "Bearer " + secret
    if config["protocol"] == "ollama":
        return config["base_url"] + "/api/chat", headers, {"model": config["model"], "messages": messages, "stream": False,
            "format": "json", "options": {"num_predict": config["max_output_tokens"], "temperature": 0.2}}
    response_format = {"type": "json_object"}
    if response_schema:
        response_format = {"type": "json_schema", "json_schema": {
            "name": schema_name, "strict": True, "schema": response_schema}}
    return config["base_url"] + "/chat/completions", headers, {"model": config["model"], "messages": messages,
        "max_tokens": config["max_output_tokens"], "temperature": 0.2, "response_format": response_format}


def complete_json(*, system, user, context=None, connection_test=False,
        response_schema=None, schema_name="sys_response", response_validator=None):
    context = context or {}
    now = datetime.now(timezone.utc)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    with database.SessionLocal() as db:
        # A write lock serializes reservations, including on SQLite.
        changed = db.query(models.AIProviderSettings).filter_by(id=1).update({models.AIProviderSettings.revision: models.AIProviderSettings.revision}, synchronize_session=False)
        if not changed:
            raise HTTPException(503, "Configure an AI provider in administrator settings first")
        row = get_config(db)
        if not row.enabled and not connection_test:
            raise HTTPException(503, "Live AI is disabled; saved lessons remain available")
        config = public_config(row)
        validate_base(row.protocol, row.base_url)
        try:
            secret = cipher().decrypt(row.encrypted_key.encode()).decode() if row.encrypted_key else ""
        except InvalidToken:
            raise HTTPException(503, "AI credential cannot be decrypted; ask the administrator to re-enter it")
        if row.protocol == "openai_compatible" and not secret:
            raise HTTPException(503, "No API key configured")
        if connection_test:
            config["max_output_tokens"] = min(config["max_output_tokens"], 128)
        url, headers, body = _request(config, secret, system, user, context,
            response_schema=response_schema, schema_name=schema_name)
        # Conservative local admission estimate. Provider accounting remains authoritative.
        reserved = estimated_reservation(body, config["max_output_tokens"])
        actor = db.get(models.User, context.get("actor_id")) if context.get("actor_id") else None
        events = db.query(models.AIUsageEvent).filter(models.AIUsageEvent.created_at >= day)
        used_requests, used_tokens = events.with_entities(func.count(models.AIUsageEvent.id), func.coalesce(func.sum(models.AIUsageEvent.budget_tokens), 0)).one()
        recent = db.query(models.AIUsageEvent).filter(models.AIUsageEvent.created_at >= now - timedelta(minutes=1))
        minute_requests, minute_tokens = recent.with_entities(func.count(models.AIUsageEvent.id), func.coalesce(func.sum(models.AIUsageEvent.budget_tokens), 0)).one()
        if used_requests >= row.daily_requests or used_tokens + reserved > row.daily_tokens:
            raise HTTPException(429, "SYS daily AI budget reached; saved lessons remain available", headers={"Retry-After": "60"})
        if minute_requests >= row.minute_requests or minute_tokens + reserved > row.minute_tokens:
            raise HTTPException(429, "SYS AI request budget is busy or this prompt is too large; try later or shorten it", headers={"Retry-After": "60"})
        if actor and (actor.role or "").lower() == "student" and events.filter(models.AIUsageEvent.actor_id == actor.id).count() >= row.student_daily_requests:
            raise HTTPException(429, "Your daily live-AI allowance is reached; saved lessons remain available")
        event = models.AIUsageEvent(actor_id=actor.id if actor else None, model=row.model, provider_label=row.label,
            purpose="CONNECTION_TEST" if connection_test else str(context.get("intent", "OTHER"))[:64],
            status="RESERVED", budget_tokens=reserved, created_at=now)
        db.add(event); db.commit(); event_id = event.id
    error = None; total = None; result = None; contract_error = None
    try:
        # No redirects or environment proxy inheritance: credentials stay at the approved endpoint.
        with httpx.Client(timeout=httpx.Timeout(45, connect=10), follow_redirects=False, trust_env=False) as client:
            response = client.post(url, headers=headers, json=body)
        if response.status_code != 200:
            error = "HTTP_" + str(response.status_code)
        elif len(response.content) > 1_000_000:
            error = "RESPONSE_TOO_LARGE"
        else:
            payload = response.json()
            if config["protocol"] == "ollama":
                content = payload["message"]["content"]
                if "prompt_eval_count" in payload and "eval_count" in payload:
                    total = payload["prompt_eval_count"] + payload["eval_count"]
            else:
                content = payload["choices"][0]["message"]["content"]
                total = (payload.get("usage") or {}).get("total_tokens")
            if not isinstance(total, int) or isinstance(total, bool) or total < 0:
                total = None
            result = json.loads(content)
            if not isinstance(result, dict):
                error = "INVALID_JSON_OBJECT"
            elif response_validator:
                try:
                    response_validator(result)
                except HTTPException as validation_error:
                    error = "CONTRACT_VALIDATION_FAILED"
                    contract_error = validation_error
    except httpx.TimeoutException:
        error = "TIMEOUT"
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        error = "INVALID_RESPONSE_OR_NETWORK"
    with database.SessionLocal() as db:
        event = db.get(models.AIUsageEvent, event_id)
        event.status = "FAILED" if error else "SUCCEEDED"
        event.error_code = error
        event.total_tokens = total
        event.budget_tokens = total if total is not None else reserved
        event.finished_at = datetime.now(timezone.utc)
        db.commit()
    if contract_error:
        raise contract_error
    if error:
        raise HTTPException(502, f"AI provider request failed ({error}). Saved lessons remain available. Usage reference: {event_id}")
    return result


def usage_summary(db):
    now = datetime.now(timezone.utc)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.query(models.AIUsageEvent).filter(models.AIUsageEvent.created_at >= day).all()
    recent = db.query(models.AIUsageEvent).order_by(models.AIUsageEvent.id.desc()).limit(50).all()
    user_usage = (db.query(models.User.id, models.User.name, models.User.role, func.count(models.AIUsageEvent.id), func.sum(models.AIUsageEvent.budget_tokens))
        .join(models.AIUsageEvent, models.AIUsageEvent.actor_id == models.User.id)
        .filter(models.AIUsageEvent.created_at >= day)
        .group_by(models.User.id, models.User.name, models.User.role)
        .order_by(func.sum(models.AIUsageEvent.budget_tokens).desc(), models.User.id).limit(100).all())
    return {"date_utc": day.date().isoformat(), "requests": len(rows),
        "by_user": [{"user_id": uid, "name": name, "role": role, "requests": requests, "budget_tokens": tokens}
                    for uid, name, role, requests, tokens in user_usage],
        "by_purpose": [{"purpose": purpose, "requests": sum(r.purpose == purpose for r in rows),
                        "budget_tokens": sum(r.budget_tokens for r in rows if r.purpose == purpose)}
                       for purpose in sorted({r.purpose for r in rows})],
        "measured_tokens": sum(r.total_tokens or 0 for r in rows),
        "budget_tokens": sum(r.budget_tokens for r in rows),
        "estimated_requests": sum(r.total_tokens is None for r in rows),
        "failed_requests": sum(r.status == "FAILED" for r in rows),
        "limits": public_config(get_config(db)),
        "recent": [{k: getattr(r, k) for k in ("id", "created_at", "provider_label", "model", "purpose", "status", "total_tokens", "budget_tokens", "error_code")} for r in recent]}
