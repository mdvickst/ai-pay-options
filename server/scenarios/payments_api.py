import asyncio
import uuid
from typing import Any, Literal

from agents import RunContextWrapper, function_tool
from fastapi import APIRouter, Request, Response

from server import events
from server.config import PaymentsApiConfig, get_config
from server.scenarios import spawn
from server.settings import public_url, settings
from server.state import CallState, balance_for, get_call
from server.twilio_client import client

router = APIRouter()
CaptureField = Literal["payment-card-number", "expiration-date", "security-code", "postal-code"]
FIELD_NAMES = {
    "payment-card-number": "card number",
    "expiration-date": "expiration date",
    "security-code": "security code",
    "postal-code": "billing zip code",
}
VALUE_NAMES = {
    "payment-card-number": "PaymentCardNumber",
    "expiration-date": "ExpirationDate",
    "security-code": "SecurityCode",
    "postal-code": "PaymentCardPostalCode",
}
AMEX_SECURITY_PROMPT = "Now enter the four digit security code on the front of your card."
ERROR_LINES = {
    "input-timeout": "It sounds like the entry stopped partway.",
    "timeout": "It sounds like the entry stopped partway.",
    "invalid-card-number": "That card number didn't go through.",
    "invalid-card-type": "Sorry, we can't accept that type of card.",
    "invalid-date": "That expiration date didn't work.",
    "invalid-security-code": "That security code didn't look right.",
    "invalid-postal-code": "That zip code didn't look right.",
}
FAILURE_REASONS = (
    ("declined", "your card was declined"),
    ("invalid", "the card number wasn't valid"),
    ("expired", "the card has expired"),
    ("interrupted-with-star", "the payment was cancelled"),
    ("hung-up", "the call ended before the payment finished"),
    ("too-many-failed-attempts", "there were too many unsuccessful attempts"),
    ("validation-error", "some of the card details couldn't be verified"),
    ("payment-connector-error", "the payment processor couldn't complete the charge"),
)
PUBLISHED_FIELDS = (
    "Capture", "PartialResult", "Required", "ErrorType", "PaymentCardNumber", "PaymentCardType", "ExpirationDate",
    "PaymentCardPostalCode", "SecurityCode", "Result", "PaymentConfirmationCode", "PaymentError", "PayErrorCode",
)


def field_order(cfg: PaymentsApiConfig) -> list[str]:
    """Capture order for the configured session."""
    order = ["payment-card-number", "expiration-date"]
    if cfg.security_code:
        order.append("security-code")
    if cfg.postal_code:
        order.append("postal-code")
    return order


def prompt_for(call: CallState, field: str) -> str:
    """Spoken prompt for a capture field, using the Amex security-code wording when the card is Amex."""
    if field == "security-code" and call.pay_data.get("card_type") == "amex":
        return AMEX_SECURITY_PROMPT
    return get_config().payments_api.field_prompts[field]


def error_line(error: str, field: str, digits: int) -> str:
    """Spoken lead-in for a re-prompt after a capture error."""
    line = ERROR_LINES.get(error, f"That {FIELD_NAMES.get(field, 'entry')} didn't go through.")
    if field == "payment-card-number" and error in ("invalid-card-number", "input-timeout", "timeout") and digits:
        line += f" I got {digits} digits; most cards have 16, and American Express has 15."
    return line + " Let's try that again."


def next_field(cfg: PaymentsApiConfig, required: str) -> str | None:
    """First field still listed in a callback's Required value, in capture order."""
    pending = set(required.split(","))
    return next((f for f in field_order(cfg) if f in pending), None)


def result_line(call: CallState, form: dict[str, str]) -> str:
    """Spoken sentence for a final Payments API result, without confirmation codes or raw error codes."""
    if form["Result"] == "success":
        return f"Your payment of ${balance_for(call):.2f} was successful. Is there anything else I can help you with?"
    detail = " ".join(form.get(k, "") for k in ("PaymentError", "ConnectorError", "PayErrorCode", "Result")).lower()
    reason = next((text for key, text in FAILURE_REASONS if key in detail), "the payment didn't go through")
    return f"Sorry, {reason}, so nothing was charged. Would you like to try again?"


def digits_entered(call: CallState, field: str | None) -> int:
    """Returns how many keys the caller has pressed so far for the field."""
    return call.pay_data.get("digits", {}).get(field or "", 0)


def payment_progress(call: CallState) -> dict[str, Any]:
    """Returns the current capture field, keys pressed for it, and fields captured so far."""
    captured = call.pay_data.get("captured", [])
    return {
        "active": bool(call.payment_sid),
        "current_field": call.payment_field,
        "digits_entered": digits_entered(call, call.payment_field),
        "captured_fields": captured,
        "remaining_fields": [f for f in field_order(get_config().payments_api) if f not in captured],
    }


def payment_state_note(call: CallState) -> str:
    """One-line payment state prepended to caller speech while a session is active."""
    p = payment_progress(call)
    current = FIELD_NAMES.get(p["current_field"] or "", "nothing")
    done = ", ".join(FIELD_NAMES[f] for f in p["captured_fields"]) or "nothing yet"
    return f"[PAYMENT STATE] Keypad capture is waiting for the {current}; {p['digits_entered']} digits entered so far. Captured: {done}."


async def _update(call: CallState, **kwargs: Any) -> None:
    await asyncio.to_thread(
        lambda: client.calls(call.call_sid).payments(call.payment_sid).update(
            idempotency_key=uuid.uuid4().hex, status_callback=public_url("/payments/status"), **kwargs
        )
    )


def _end_session(call: CallState) -> None:
    cancel_no_input(call)
    call.payment_sid, call.payment_field = None, None


def _call_gone(exc: Exception) -> bool:
    return "21220" in str(exc) or "not in the expected state" in str(exc)


async def start(call: CallState) -> str:
    """Creates a Payments API session and starts the server-driven capture sequence; returns the tool result for the agent."""
    if call.payment_sid:
        return "A payment is already in progress. Do not start another one."
    cfg = get_config().payments_api
    amount = balance_for(call)
    kwargs: dict[str, Any] = {
        "idempotency_key": uuid.uuid4().hex,
        "status_callback": public_url("/payments/status"),
        "payment_connector": cfg.payment_connector or settings.pay_connector,
        "valid_card_types": cfg.valid_card_types,
        "postal_code": cfg.postal_code,
        "security_code": cfg.security_code,
        "timeout": cfg.timeout,
    }
    if cfg.charge:
        kwargs["charge_amount"] = amount
    else:
        kwargs["token_type"] = cfg.token_type
    if cfg.confirmation:
        kwargs["confirmation"] = "true"
    try:
        payment = await asyncio.to_thread(lambda: client.calls(call.call_sid).payments.create(**kwargs))
    except Exception as exc:
        events.publish("error", "Payments API create failed", {"error": str(exc)}, call.call_sid)
        return "Starting the payment failed. Apologize and say the payment system is unavailable right now."
    call.payment_sid, call.payment_field = payment.sid, None
    call.pay_data = {"digits": {}, "captured": [], "attempts": {}, "no_input": 0, "card_type": ""}
    events.publish("payment", "Payment session created", {"sid": payment.sid, "amount": amount}, call.call_sid)
    spawn(capture(call, field_order(cfg)[0], lead=f"Okay, I'll take a payment of ${amount:.2f}. "))
    return "The secure keypad payment has started and the system is prompting the caller now. Say nothing this turn."


async def capture(call: CallState, field: str, lead: str = "") -> None:
    """Arms keypad capture for a field, speaks its prompt, and starts the no-input timer."""
    if call.ended or not call.payment_sid:
        return
    cancel_no_input(call)
    try:
        await _update(call, capture=field)
    except Exception as exc:
        await _update_failed(call, f"Capture {field}", exc)
        return
    call.payment_field = field
    call.pay_data["digits"][field] = 0
    events.publish("payment", f"Capture {field}", call_sid=call.call_sid)
    from server.agent import say

    await say(call, lead + prompt_for(call, field))
    if call.payment_field == field and not digits_entered(call, field):
        arm_no_input(call)


async def complete(call: CallState) -> None:
    """Tells the caller the payment is processing and submits it to the connector."""
    from server.agent import say

    cancel_no_input(call)
    call.payment_field = None
    await say(call, "Thanks, I have everything. One moment while I process your payment.")
    try:
        await _update(call, status="complete")
        events.publish("payment", "Payment submitted", call_sid=call.call_sid)
    except Exception as exc:
        await _update_failed(call, "Complete payment", exc)


async def give_up(call: CallState, reason: str) -> None:
    """Cancels the session and hands the conversation back to the agent with the reason."""
    from server.agent import run_turn

    if call.payment_sid:
        try:
            await _update(call, status="cancel")
        except Exception:
            pass
    _end_session(call)
    events.publish("payment", "Payment stopped", {"reason": reason}, call.call_sid)
    if not call.ended:
        await run_turn(call, f"[PAYMENT EVENT] The keypad payment was stopped: {reason}. Nothing was charged. In one or two short sentences, apologize and ask whether they want to try again.")


async def _update_failed(call: CallState, what: str, exc: Exception) -> None:
    events.publish("error", f"{what} failed", {"error": str(exc)[:300]}, call.call_sid)
    if _call_gone(exc):
        call.ended = True
        _end_session(call)
        return
    await give_up(call, "the payment system returned an error")


def cancel_no_input(call: CallState) -> None:
    """Stops the no-input timer for the call."""
    if call.no_input_task and call.no_input_task is not asyncio.current_task():
        call.no_input_task.cancel()
    call.no_input_task = None


def arm_no_input(call: CallState) -> None:
    """Restarts the no-input timer for the field being captured."""
    cancel_no_input(call)
    if call.payment_field and not call.ended:
        call.no_input_task = asyncio.create_task(_no_input(call, call.payment_field))


async def _no_input(call: CallState, field: str) -> None:
    from server.agent import say

    cfg = get_config().payments_api
    await asyncio.sleep(cfg.no_input_seconds)
    call.no_input_task = None
    if call.ended or call.payment_field != field or digits_entered(call, field):
        return
    call.pay_data["no_input"] += 1
    events.publish("payment", f"No input for {field}", {"count": call.pay_data["no_input"]}, call.call_sid)
    if call.pay_data["no_input"] > cfg.max_no_input_retries:
        await give_up(call, f"no keypad input for the {FIELD_NAMES[field]}")
        return
    await say(call, "I didn't catch any key presses. " + prompt_for(call, field))
    if call.payment_field == field and not digits_entered(call, field):
        arm_no_input(call)


async def handle_event(call: CallState, form: dict[str, str]) -> None:
    """Drives the capture sequence from one non-partial Payments API status callback."""
    from server.agent import say

    cfg = get_config().payments_api
    capture_field = form.get("Capture", "")
    if form.get("Result"):
        _end_session(call)
        await say(call, result_line(call, form))
        return
    if not capture_field or capture_field != call.payment_field:
        return
    cancel_no_input(call)
    if form.get("ErrorType"):
        attempts = call.pay_data["attempts"].get(capture_field, 0) + 1
        call.pay_data["attempts"][capture_field] = attempts
        if attempts >= cfg.max_attempts:
            await give_up(call, f"the caller couldn't enter a valid {FIELD_NAMES[capture_field]} after {attempts} tries")
            return
        await capture(call, capture_field, lead=error_line(form["ErrorType"], capture_field, digits_entered(call, capture_field)) + " ")
        return
    if capture_field not in call.pay_data["captured"]:
        call.pay_data["captured"].append(capture_field)
    if form.get("PaymentCardType"):
        call.pay_data["card_type"] = form["PaymentCardType"].lower()
    call.pay_data["no_input"] = 0
    upcoming = next_field(cfg, form.get("Required", ""))
    if upcoming:
        await capture(call, upcoming)
    else:
        await complete(call)


@function_tool
async def repeat_prompt(ctx: RunContextWrapper[CallState]) -> str:
    """Replay the keypad prompt for the field currently being captured, after your reply."""
    call = ctx.context
    if not call.payment_field:
        return "Nothing is being captured right now."
    spawn(capture(call, call.payment_field))
    return "The prompt will play right after your reply. Keep your reply to one short sentence, or say nothing."


@function_tool
async def recapture_field(ctx: RunContextWrapper[CallState], field: CaptureField) -> str:
    """Restart keypad entry for a field the caller says they entered wrong. The prompt plays after your reply.

    Args:
        field: The payment field to capture again.
    """
    call = ctx.context
    if not call.payment_sid:
        return "No payment is in progress."
    if field in call.pay_data["captured"]:
        call.pay_data["captured"].remove(field)
    spawn(capture(call, field))
    return f"Re-capturing the {FIELD_NAMES[field]}. Its prompt will play right after your reply. Keep your reply to one short sentence."


@function_tool
async def get_payment_progress(ctx: RunContextWrapper[CallState]) -> dict[str, Any]:
    """Check how many digits the caller has entered for the field being captured, and which fields are done."""
    return payment_progress(ctx.context)


@function_tool
async def cancel_payment(ctx: RunContextWrapper[CallState]) -> str:
    """Cancel the active payment without charging the caller."""
    call = ctx.context
    if call.payment_sid:
        try:
            await _update(call, status="cancel")
        except Exception as exc:
            events.publish("error", "Cancel payment failed", {"error": str(exc)[:300]}, call.call_sid)
    _end_session(call)
    events.publish("payment", "Payment cancelled", call_sid=call.call_sid)
    return "Payment cancelled. Nothing was charged."


TOOLS = [repeat_prompt, recapture_field, get_payment_progress, cancel_payment]


@router.post("/payments/status")
async def payments_status(request: Request) -> Response:
    """Payments API status callback: tracks keypresses and advances the capture sequence."""
    form = {k: str(v) for k, v in (await request.form()).items()}
    call = get_call(form["CallSid"])
    payload = {k: form[k] for k in PUBLISHED_FIELDS if form.get(k)}
    if call.ended:
        return Response(status_code=200)
    if form.get("PartialResult") == "true":
        capture_field = form.get("Capture", "")
        if capture_field in VALUE_NAMES and capture_field == call.payment_field:
            call.pay_data["digits"][capture_field] = len(form.get(VALUE_NAMES[capture_field], ""))
            cancel_no_input(call)
        payload["digits_entered"] = digits_entered(call, capture_field)
        events.publish("payment", "Payments API callback", payload, call.call_sid)
        return Response(status_code=200)
    events.publish("payment", "Payments API callback", payload, call.call_sid)
    if call.payment_sid:
        spawn(handle_event(call, form))
    return Response(status_code=200)
