from fastapi import APIRouter, Request, Response

from server import events
from server.agent import GREETING
from server.config import get_config
from server.http_util import xml
from server.state import end_call_state, get_call
from server.tac_app import agent_relay_options, voice_channel

router = APIRouter()


@router.post("/voice/incoming")
async def voice_incoming(request: Request) -> Response:
    """TwiML App / phone number voice URL: connects the caller to the ACME agent."""
    form = await request.form()
    call = get_call(str(form["CallSid"]))
    call.caller_number = str(form.get("callerNumber") or form.get("From") or "unknown")
    call.history = [{"role": "assistant", "content": GREETING}]
    events.publish("call", "Incoming call", {"from": form.get("From"), "callerNumber": call.caller_number, "scenario": get_config().scenario}, call.call_sid)
    twiml = await voice_channel.handle_incoming_call(host_twiml_options=agent_relay_options(GREETING))
    return xml(twiml)


@router.post("/voice/status")
async def voice_status(request: Request) -> Response:
    """Call status callback: publishes status and clears state when the call completes."""
    form = await request.form()
    call_sid, status = str(form.get("CallSid")), str(form.get("CallStatus"))
    events.publish("call", f"Call {status}", call_sid=call_sid)
    if status == "completed":
        end_call_state(call_sid)
    return Response(status_code=204)
