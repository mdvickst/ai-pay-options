import random

from fastapi import APIRouter, Request, Response

from server import events
from server.card_parse import ERROR_TEXT, check_field, extract_digits, mask, mask_text
from server.config import get_config
from server.http_util import xml
from server.return_to_agent import failure_outcome, return_to_agent_twiml, success_outcome
from server.scenarios import schedule_redirect
from server.state import CallState, balance_for, get_call
from server.twilio_client import update_call
from server.twiml_builders import GATHER_FIELDS, build_gather_twiml

router = APIRouter()


async def redirect(call: CallState) -> None:
    """Moves the live call to the first <Gather> step."""
    await update_call(call.call_sid, twiml=build_gather_twiml(get_config().gather, "card", 1))


async def start(call: CallState) -> str:
    """Resets gather progress, schedules the redirect, and returns the hand-off instruction."""
    call.pay_data = {}
    return schedule_redirect(call, redirect)


@router.post("/gather/result")
async def gather_result(request: Request, field: str, attempt: int) -> Response:
    """Validates one <Gather> result, then advances, retries, or returns to the agent."""
    form = {k: str(v) for k, v in (await request.form()).items()}
    call = get_call(form["CallSid"])
    cfg = get_config().gather
    keyed, speech = form.get("Digits", ""), form.get("SpeechResult", "")
    digits = keyed or extract_digits(speech, months=field == "expiry")
    events.publish(
        "payment",
        f"<Gather> {field} attempt {attempt}",
        {
            "source": "dtmf" if keyed else ("speech" if speech else "none"),
            "speech": mask_text(speech) if cfg.show_raw_speech and speech else None,
            "digits": mask(digits),
            "confidence": form.get("Confidence"),
        },
        call.call_sid,
    )
    result = check_field(field, digits, call.pay_data.get("brand"))
    if result.ok:
        call.pay_data.update({k: v for k, v in result.info.items() if k in ("brand", "last4")})
        index = GATHER_FIELDS.index(field)
        if index + 1 < len(GATHER_FIELDS):
            return xml(build_gather_twiml(cfg, GATHER_FIELDS[index + 1], 1, call.pay_data.get("brand")))
        code = f"{random.randint(0, 999999):06d}"
        events.publish("payment", "Mock charge approved", {"last4": call.pay_data.get("last4"), "code": code}, call.call_sid)
        return xml(await return_to_agent_twiml(call, success_outcome(balance_for(call), call.pay_data.get("last4"), code)))
    events.publish("payment", f"{field} rejected: {result.error}", call_sid=call.call_sid)
    if attempt >= cfg.max_attempts:
        return xml(await return_to_agent_twiml(call, failure_outcome()))
    return xml(build_gather_twiml(cfg, field, attempt + 1, call.pay_data.get("brand"), prefix=ERROR_TEXT[result.error]))
