from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from server import events
from server.config import DemoConfig, PayVerbConfig, get_config, set_config
from server.settings import settings
from server.twiml_builders import build_pay_twiml

router = APIRouter(prefix="/api")


@router.get("/config")
def read_config() -> DemoConfig:
    """Returns the active demo config."""
    return get_config()


@router.put("/config")
def write_config(cfg: DemoConfig) -> DemoConfig:
    """Replaces the active demo config."""
    set_config(cfg)
    events.publish("call", f"Config saved, active scenario: {cfg.scenario}")
    return cfg


@router.post("/preview/pay")
def preview_pay(cfg: PayVerbConfig) -> dict:
    """Renders <Pay> TwiML for the given scenario 1 config with a sample amount."""
    return {"twiml": build_pay_twiml(cfg, 87.42)}


@router.get("/token")
def token() -> dict:
    """Returns a Voice SDK access token for the browser softphone."""
    access = AccessToken(settings.account_sid, settings.api_key, settings.api_secret, identity="acme-demo", ttl=3600)
    access.add_grant(VoiceGrant(outgoing_application_sid=settings.twiml_app_sid))
    return {"token": access.to_jwt(), "identity": "acme-demo"}


@router.get("/events")
def event_stream() -> StreamingResponse:
    """Server-Sent Events feed of call, agent, tool, and payment events."""
    return StreamingResponse(events.stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
