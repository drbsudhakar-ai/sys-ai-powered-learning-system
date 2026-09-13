"""AI control-plane integration tests. HTTP provider responses are simulated."""
import json
import os
import unittest
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import database, models
from app.main import app
from app.services import ai_gateway, ai_lecturer
from app.services.ai_provider import ConfiguredAIProvider, get_ai_provider
from app.services.ai_lesson_contract import (
    LESSON_RESPONSE_SCHEMA,
    explanation_step,
    lesson_plan,
    validate_lesson_response,
    validate_explanation_response,
)
from tests.auth_helpers import ProtectedUserFactory

client = TestClient(app)
users = ProtectedUserFactory(client, "AIGATE")


def deep_lesson_steps(prefix="Part"):
    return [{"title": f"{prefix} {i + 1}",
        "explanation": ("Detailed board explanation connects the concept to the approved syllabus. " * 3).strip(),
        "narration": ("The lecturer develops this idea progressively, explains why it matters, and connects it to a clear example for the learner. " * 8).strip(),
        "bullets": ["Core concept", "Applied example"], "formula": None, "flow": [], "model_3d": None}
        for i in range(8)]


class AIManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = users.create("admin")
        cls.student = users.create("student", {"roll_number": "AIGATESTUDENT"})
        cls.faculty = users.create("faculty", {"employee_code": "AIGATEFACULTY"})

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"SYS_AI_ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "SYS_AI_PROVIDER": "configured", "SYS_AI_ALLOWED_BASE_URLS": ai_gateway.DEFAULT_BASES,
            "SYS_AI_OLLAMA_BASE_URL": "http://127.0.0.1:11434"}))
        with database.SessionLocal() as db:
            db.query(models.AIUsageEvent).delete()
            db.query(models.AIProviderSettings).delete()
            db.commit()
        self.payload = dict(label="Pilot", protocol="openai_compatible", base_url="https://api.groq.com/openai/v1",
            model="test-model", enabled=True, api_key="test-only-not-real-key", expected_revision=0,
            daily_requests=100, daily_tokens=150000, minute_requests=10, minute_tokens=50000,
            student_daily_requests=2, max_output_tokens=500)

    def tearDown(self):
        with database.SessionLocal() as db:
            db.query(models.AIUsageEvent).delete()
            db.query(models.AIProviderSettings).delete()
            db.commit()

    def headers(self, user=None):
        return {"Authorization": "Bearer " + (user or self.admin).token}

    def save(self, **changes):
        self.payload.update(changes)
        response = client.put("/admin/ai/provider", headers=self.headers(), json=self.payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("test-only-not-real-key", response.text)
        self.assertNotIn("encrypted_key", response.text)
        self.payload["expected_revision"] = response.json()["revision"]
        return response.json()

    def response(self, content=None, total=42):
        result = {"choices": [{"message": {"content": json.dumps(content or {"ok": True})}}]}
        if total is not None:
            result["usage"] = {"total_tokens": total}
        return httpx.Response(200, json=result)

    def request(self, actor=None):
        return ai_gateway.complete_json(system="JSON only", user="Explain arithmetic", context={"actor_id": (actor or self.student).user_id, "intent": "ASK_QUESTION"})

    def test_all_endpoints_admin_only(self):
        for user in (self.student, self.faculty):
            for method, path in (("get", "/provider"), ("put", "/provider"), ("post", "/provider/test"), ("get", "/usage")):
                response = getattr(client, method)("/admin/ai" + path, headers=self.headers(user), **({"json": self.payload} if method == "put" else {}))
                self.assertEqual(response.status_code, 403)
        self.assertEqual(client.get("/admin/ai/usage").status_code, 401)

    def test_encrypted_key_redaction_and_revision(self):
        saved = self.save()
        self.assertTrue(saved["has_api_key"])
        with database.SessionLocal() as db:
            stored = db.get(models.AIProviderSettings, 1).encrypted_key
            self.assertNotIn(self.payload["api_key"], stored)
            self.assertEqual(ai_gateway.cipher().decrypt(stored.encode()).decode(), self.payload["api_key"])
            audit = db.query(models.AdminAuditLog).filter_by(action="ai.settings.updated").order_by(models.AdminAuditLog.id.desc()).first()
            self.assertNotIn(self.payload["api_key"], json.dumps(audit.details))
        bad = {**self.payload, "expected_revision": 0}
        self.assertEqual(client.put("/admin/ai/provider", headers=self.headers(), json=bad).status_code, 409)

    def test_validation_errors_never_echo_secrets(self):
        bad = {**self.payload, "api_key": {"secret": "never-echo-this"}}
        response = client.put("/admin/ai/provider", headers=self.headers(), json=bad)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("never-echo-this", response.text)

    def test_unapproved_endpoint_and_missing_encryption(self):
        for base in ("http://169.254.169.254", "https://api.groq.com/openai/v1?secret=yes", "https://evil.example"):
            response = client.put("/admin/ai/provider", headers=self.headers(), json={**self.payload, "base_url": base})
            self.assertEqual(response.status_code, 422)
        with patch.dict(os.environ, {"SYS_AI_ENCRYPTION_KEY": ""}):
            response = client.put("/admin/ai/provider", headers=self.headers(), json=self.payload)
            self.assertEqual(response.status_code, 503)

    def test_destination_change_clears_old_key(self):
        self.save()
        saved = self.save(base_url="https://api.openai.com/v1", api_key=None, enabled=False)
        self.assertFalse(saved["has_api_key"])

    def test_hosted_adapter_and_actual_usage(self):
        self.save()
        with patch.object(httpx.Client, "post", return_value=self.response()) as call:
            self.assertEqual(self.request(), {"ok": True})
        self.assertEqual(call.call_args.args[0], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(call.call_args.kwargs["headers"]["Authorization"], "Bearer test-only-not-real-key")
        self.assertNotIn("actor_id", json.dumps(call.call_args.kwargs["json"]))
        summary = client.get("/admin/ai/usage", headers=self.headers()).json()
        self.assertEqual(summary["requests"], 1)
        self.assertEqual(summary["measured_tokens"], 42)
        self.assertEqual(summary["budget_tokens"], 42)
        self.assertNotIn("Explain arithmetic", json.dumps(summary))

    def test_hosted_adapter_sends_strict_lesson_schema(self):
        self.save(model="openai/gpt-oss-120b")
        with patch.object(httpx.Client, "post", return_value=self.response()) as call:
            ai_gateway.complete_json(system="Lesson", user="Teach", context={"intent": "TEACHING_PLAN"},
                response_schema=LESSON_RESPONSE_SCHEMA, schema_name="sys_lesson")
        response_format = call.call_args.kwargs["json"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], "sys_lesson")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertFalse(response_format["json_schema"]["schema"]["additionalProperties"])
        step = response_format["json_schema"]["schema"]["properties"]["steps"]["items"]
        self.assertFalse(step["additionalProperties"])
        self.assertEqual(set(step["required"]), set(step["properties"]))

    def test_contract_failure_is_accounted_as_failed(self):
        self.save(model="openai/gpt-oss-120b")
        with patch.object(httpx.Client, "post", return_value=self.response({"unexpected": True})):
            with self.assertRaises(HTTPException) as denied:
                ai_gateway.complete_json(system="Lesson", user="Teach", context={"intent": "TEACHING_PLAN"},
                    response_schema=LESSON_RESPONSE_SCHEMA, schema_name="sys_lesson",
                    response_validator=validate_lesson_response)
        self.assertEqual(denied.exception.status_code, 502)
        with database.SessionLocal() as db:
            event = db.query(models.AIUsageEvent).order_by(models.AIUsageEvent.id.desc()).first()
            self.assertEqual(event.status, "FAILED")
            self.assertEqual(event.error_code, "CONTRACT_VALIDATION_FAILED")

    def test_ollama_adapter(self):
        self.save(protocol="ollama", base_url="http://127.0.0.1:11434", api_key=None)
        response = httpx.Response(200, json={"message": {"content": '{"ok":true}'}, "prompt_eval_count": 10, "eval_count": 5})
        with patch.object(httpx.Client, "post", return_value=response) as call:
            self.request()
        self.assertTrue(call.call_args.args[0].endswith("/api/chat"))
        self.assertNotIn("Authorization", call.call_args.kwargs["headers"])
        self.assertEqual(client.get("/admin/ai/usage", headers=self.headers()).json()["measured_tokens"], 15)

    def test_student_limit_and_faculty_shared_limit(self):
        self.save(student_daily_requests=1, daily_requests=2)
        with patch.object(httpx.Client, "post", return_value=self.response()) as call:
            self.request()
            with self.assertRaises(HTTPException) as denied:
                self.request()
            self.assertEqual(denied.exception.status_code, 429)
            self.request(self.faculty)
            with self.assertRaises(HTTPException):
                self.request(self.admin)
            self.assertEqual(call.call_count, 2)

    def test_minute_and_token_budgets_block_before_network(self):
        self.save(minute_requests=1)
        with patch.object(httpx.Client, "post", return_value=self.response()) as call:
            self.request()
            with self.assertRaises(HTTPException):
                self.request(self.faculty)
            self.assertEqual(call.call_count, 1)
        self.save(minute_requests=10, daily_tokens=1000, max_output_tokens=1500)
        with patch.object(httpx.Client, "post") as call:
            with self.assertRaises(HTTPException):
                self.request(self.faculty)
            call.assert_not_called()

    def test_strict_schema_reservation_uses_token_estimate_not_raw_bytes(self):
        body = {"messages": [{"content": "x" * 4000}], "response_format": {
            "type": "json_schema", "json_schema": {"schema": LESSON_RESPONSE_SCHEMA}}}
        raw_bytes = len(json.dumps(body).encode())
        reserved = ai_gateway.estimated_reservation(body, 1500)
        self.assertLess(reserved, raw_bytes)
        self.assertGreaterEqual(reserved, 1500 + 256)

    def test_disabled_and_connection_test(self):
        self.save(enabled=False)
        with patch.object(httpx.Client, "post", return_value=self.response()) as call:
            with self.assertRaises(HTTPException) as denied:
                self.request()
            self.assertEqual(denied.exception.status_code, 503)
            response = client.post("/admin/ai/provider/test", headers=self.headers())
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(call.call_count, 1)

    def test_provider_failure_is_explicit_and_keeps_reservation(self):
        self.save()
        with patch.object(httpx.Client, "post", return_value=httpx.Response(429, text="upstream sensitive body")):
            with self.assertRaises(HTTPException) as denied:
                self.request()
        self.assertEqual(denied.exception.status_code, 502)
        self.assertNotIn("upstream sensitive body", denied.exception.detail)
        data = client.get("/admin/ai/usage", headers=self.headers()).json()
        self.assertEqual(data["failed_requests"], 1)
        self.assertGreater(data["budget_tokens"], 0)
        self.assertEqual(data["estimated_requests"], 1)

    def test_missing_usage_and_invalid_json(self):
        self.save()
        with patch.object(httpx.Client, "post", return_value=self.response(total=None)):
            self.request()
        bad = httpx.Response(200, json={"choices": [{"message": {"content": "not JSON"}}]})
        with patch.object(httpx.Client, "post", return_value=bad):
            with self.assertRaises(HTTPException):
                self.request()
        data = client.get("/admin/ai/usage", headers=self.headers()).json()
        self.assertEqual(data["estimated_requests"], 2)

    def test_configured_default_and_live_plan_consumption(self):
        self.assertIsInstance(get_ai_provider(), ConfiguredAIProvider)
        self.save()
        raw = {"steps": deep_lesson_steps()}
        session = SimpleNamespace(topic_id=None, subject_id=None, title="Arithmetic", objectives=[], id=12, mode="INDIVIDUAL")
        with database.SessionLocal() as db, patch.object(httpx.Client, "post", return_value=self.response(raw)):
            plan = ai_lecturer._generate_plan(db, session, self.student.user)
        self.assertEqual(plan["source"], "configured_ai")
        self.assertIn("Detailed board explanation", plan["steps"][0]["board"]["elements"][1]["text"])

    def test_schema_rejects_executable_or_incomplete_payloads(self):
        with self.assertRaises(HTTPException):
            lesson_plan({"steps": [], "javascript": "alert(1)"}, "Bad")
        with self.assertRaises(HTTPException):
            explanation_step({"answer": "", "html": "<script>"})

    def test_english_pilot_rejects_unreadable_telugu_narration(self):
        steps = deep_lesson_steps()
        steps[0]["narration"] = ("ఈ పాఠం తెలుగు లిపిలో ఉంది. " * 30).strip()
        with self.assertRaises(HTTPException):
            validate_lesson_response({"steps": steps})
        with self.assertRaises(HTTPException):
            validate_explanation_response({"answer": ("ఈ వివరణ తెలుగు లిపిలో ఉంది. " * 30).strip()})

    def test_concurrent_requests_cannot_oversubscribe_daily_budget(self):
        self.save(daily_requests=1)
        def attempt(_):
            try:
                self.request(self.admin)
                return 200
            except HTTPException as error:
                return error.status_code
        with patch.object(httpx.Client, "post", return_value=self.response()) as call, ThreadPoolExecutor(max_workers=4) as executor:
            outcomes = list(executor.map(attempt, range(4)))
            self.assertEqual(sorted(outcomes), [200, 429, 429, 429])
            self.assertEqual(call.call_count, 1)
