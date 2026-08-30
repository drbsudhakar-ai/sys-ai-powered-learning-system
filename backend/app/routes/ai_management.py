"""Administrative AI control plane; secrets never appear in responses."""
from typing import Literal
from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.orm import Session
from app import database, models
from app.routes.auth import require_roles
from app.services import ai_gateway

class SecretSafeRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def safe(request):
            try:
                return await handler(request)
            except RequestValidationError:
                # FastAPI's default validation response includes invalid input values.
                raise HTTPException(422, "Invalid AI settings. Check required fields, numeric limits and credential format.")
        return safe


router = APIRouter(prefix="/admin/ai", tags=["AI Administration"], route_class=SecretSafeRoute)
admin = require_roles("admin")


class ProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True)
    label: str = Field(min_length=1, max_length=100)
    protocol: Literal["openai_compatible", "ollama"]
    base_url: str = Field(min_length=1, max_length=500)
    model: str = Field(min_length=1, max_length=160)
    enabled: bool = False
    api_key: SecretStr | None = Field(default=None, max_length=4096)
    clear_api_key: bool = False
    expected_revision: int = Field(ge=0)
    daily_requests: int = Field(ge=1, le=1000000)
    daily_tokens: int = Field(ge=1000, le=1000000000)
    minute_requests: int = Field(ge=1, le=10000)
    minute_tokens: int = Field(ge=1000, le=10000000)
    student_daily_requests: int = Field(ge=1, le=10000)
    max_output_tokens: int = Field(ge=128, le=8192)


@router.get("/provider")
def settings(response: Response, db: Session = Depends(database.get_db), _: models.User = Depends(admin)):
    response.headers["Cache-Control"] = "no-store"
    return ai_gateway.public_config(ai_gateway.get_config(db))


@router.put("/provider")
def save(payload: ProviderUpdate, response: Response, db: Session = Depends(database.get_db), actor: models.User = Depends(admin)):
    response.headers["Cache-Control"] = "no-store"
    return ai_gateway.save_config(db, payload, actor)


@router.post("/provider/test")
def connection_test(actor: models.User = Depends(admin)):
    ai_gateway.complete_json(system='Return a JSON object only: {"ok": true}.', user="SYS connection test.",
        context={"actor_id": actor.id}, connection_test=True)
    return {"message": "Saved provider returned a valid JSON object. This test is included in usage; lesson quality still requires review."}


@router.get("/usage")
def usage(response: Response, db: Session = Depends(database.get_db), _: models.User = Depends(admin)):
    response.headers["Cache-Control"] = "no-store"
    return ai_gateway.usage_summary(db)
