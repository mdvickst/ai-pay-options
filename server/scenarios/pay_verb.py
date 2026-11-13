from fastapi import APIRouter, Request, Response

from server import events
from server.config import get_config
from server.http_util import xml
from server.return_to_agent import failure_outcome, return_to_agent_twiml, success_outcome
from server.scenarios import schedule_redirect
from server.settings import public_url
from server.state import CallState, balance_for, get_call
from server.twilio_client import update_call
from server.twiml_builders import build_pay_twiml

router = APIRouter()
PUBLISHED_FIELDS = ("Capture", "PartialResult", "Required", "ErrorType", "PaymentCardNumber", "PaymentCardType", "Result", "PaymentConfirmationCode", "PaymentError", "ConnectorError")


async def redirect(call: CallState) -> None:
    """Moves the live call to the <Pay> TwiML."""
    await update_call(call.call_sid, url=public_url("/pay/twiml"), method="POST")


async def start(call: CallState) -> str:
    """Schedules the redirect to <Pay> and returns the hand-off instruction."""
    return schedule_redirect(call, redirect)


async def _form(request: Request) -> dict[str, str]:
    return {k: str(v) for k, v in (await request.form()).items()}


@router.post("/pay/twiml")
async def pay_twiml(request: Request) -> Response:
    """Serves <Pay> built from the current scenario 1 config."""
    form = await _form(request)
    call = get_call(form["CallSid"])
    twiml = build_pay_twiml(get_config().pay_verb, balance_for(call))
    events.publish("twiml", "<Pay> TwiML", {"twiml": twiml}, call.call_sid)
    return xml(twiml)


@router.post("/pay/status")
async def pay_status(request: Request) -> Response:
    """<Pay> statusCallback: publishes masked progress."""
    form = await _form(request)
    events.publish("payment", "<Pay> status", {k: form[k] for k in PUBLISHED_FIELDS if form.get(k)}, form.get("CallSid"))
    return Response(status_code=200)


@router.post("/pay/action")
async def pay_action(request: Request) -> Response:
    """<Pay> action: reports the result and returns the caller to the agent."""
    form = await _form(request)
    call = get_call(form["CallSid"])
    result = form.get("Result", "")
    events.publish("payment", f"<Pay> finished: {result}", {k: form[k] for k in PUBLISHED_FIELDS if form.get(k)}, call.call_sid)
    if result == "success":
        last4 = (form.get("PaymentCardNumber") or "")[-4:] or None
        outcome = success_outcome(balance_for(call), last4, form.get("PaymentConfirmationCode"))
    elif result == "caller-interrupted-with-star":
        outcome = "No problem, I stopped the payment, so nothing was charged."
    else:
        outcome = failure_outcome()
    return xml(await return_to_agent_twiml(call, outcome))
