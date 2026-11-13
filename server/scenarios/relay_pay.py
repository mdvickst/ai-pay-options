import asyncio
import json
import random

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect

from server import events
from server.card_parse import BRAND_NAMES, ERROR_TEXT, check_field, expected_length, extract_digits, mask, mask_text, spaced
from server.config import RelayPayConfig, get_config
from server.http_util import xml
from server.return_to_agent import failure_outcome, return_to_agent_twiml, success_outcome
from server.scenarios import schedule_redirect
from server.state import CallState, balance_for, get_call
from server.twilio_client import update_call
from server.twiml_builders import build_relay_pay_twiml

router = APIRouter()
FIELDS = ["card", "expiry", "cvv", "zip"]
YES = {"yes", "yeah", "yep", "correct", "sure", "right", "1"}
NO = {"no", "nope", "wrong", "2"}


async def redirect(call: CallState) -> None:
    """Moves the live call to the payment ConversationRelay session."""
    await update_call(call.call_sid, twiml=build_relay_pay_twiml(get_config().relay_pay))


async def start(call: CallState) -> str:
    """Schedules the redirect to the payment socket and returns the hand-off instruction."""
    return schedule_redirect(call, redirect)


class RelayPaySession:
    """Deterministic card-capture state machine for one payment ConversationRelay socket. No LLM."""

    def __init__(self, call: CallState, cfg: RelayPayConfig, ws: WebSocket) -> None:
        self.call, self.cfg, self.ws = call, cfg, ws
        self.index = 0
        self.buffer = ""
        self.attempts = 0
        self.brand: str | None = None
        self.last4: str | None = None
        self.timer: asyncio.Task | None = None
        self.done = False

    @property
    def field(self) -> str:
        """Current field name, or "confirm" after all fields are captured."""
        return FIELDS[self.index] if self.index < len(FIELDS) else "confirm"

    async def say(self, text: str) -> None:
        """Speaks text to the caller."""
        await self.ws.send_json({"type": "text", "token": text, "last": True})

    def cancel_timer(self) -> None:
        """Stops the pending settle/no-input timer."""
        if self.timer and self.timer is not asyncio.current_task():
            self.timer.cancel()
        self.timer = None

    def arm(self, seconds: float) -> None:
        """Evaluates the current buffer after `seconds` without new input."""
        self.cancel_timer()

        async def fire() -> None:
            await asyncio.sleep(seconds)
            self.timer = None
            await self.evaluate()

        self.timer = asyncio.create_task(fire())

    async def prompt(self, text: str) -> None:
        """Speaks a field prompt and starts the no-input timer."""
        await self.say(text)
        self.arm(self.cfg.no_input_seconds)

    async def on_text(self, text: str) -> None:
        """Handles a final transcript from ConversationRelay."""
        if self.done:
            return
        if self.field == "confirm":
            await self.on_confirm(text)
            return
        await self.add(extract_digits(text, months=self.field == "expiry"), "speech", text)

    async def on_dtmf(self, digit: str) -> None:
        """Handles a keypad press from ConversationRelay."""
        if self.done:
            return
        if self.field == "confirm":
            await self.on_confirm(digit)
        elif digit == "#":
            await self.evaluate()
        elif digit.isdigit():
            await self.add(digit, "dtmf")

    async def add(self, digits: str, source: str, raw: str | None = None) -> None:
        """Appends heard digits and evaluates once the field is complete or input settles."""
        self.buffer += digits
        events.publish(
            "payment",
            f"Heard {self.field}",
            {"source": source, "speech": mask_text(raw) if raw else None, "buffer": mask(self.buffer)},
            self.call.call_sid,
        )
        if self.buffer and len(self.buffer) >= expected_length(self.field, self.brand, self.buffer):
            await self.evaluate()
        else:
            self.arm(self.cfg.settle_seconds if self.buffer else self.cfg.no_input_seconds)

    async def evaluate(self) -> None:
        """Validates the buffer for the current field, then advances or re-prompts."""
        self.cancel_timer()
        field, digits = self.field, self.buffer
        if field == "confirm":
            return
        self.buffer = ""
        result = check_field(field, digits, self.brand)
        if result.ok:
            self.attempts = 0
            if field == "card":
                self.brand, self.last4 = result.info["brand"], result.info["last4"]
            events.publish("payment", f"{field} accepted", result.info, self.call.call_sid)
            self.index += 1
            if self.field == "confirm":
                await self.say(
                    self.cfg.prompts["confirm"].format(
                        brand=BRAND_NAMES.get(self.brand or "unknown", "card"),
                        last4=spaced(self.last4 or ""),
                        amount=f"{balance_for(self.call):.2f}",
                    )
                )
            else:
                await self.prompt(self.cfg.prompts[self.field])
            return
        self.attempts += 1
        events.publish("payment", f"{field} rejected", {"error": result.error, "attempt": self.attempts}, self.call.call_sid)
        if self.attempts >= self.cfg.max_attempts:
            await self.finish(False)
            return
        await self.prompt(f"{ERROR_TEXT[result.error]} {self.cfg.prompts[field]}")

    async def on_confirm(self, text: str) -> None:
        """Handles the yes/no confirmation of the last four digits."""
        words = set(text.lower().replace(".", " ").replace(",", " ").split())
        if words & YES:
            await self.finish(True)
        elif words & NO:
            self.index, self.brand, self.last4, self.attempts = 0, None, None, 0
            await self.prompt(f"No problem, let's start over. {self.cfg.prompts['card']}")
        else:
            await self.say("Please say yes or no.")

    async def finish(self, ok: bool) -> None:
        """Mock-charges on success and ends the session with the outcome as handoff data."""
        self.done = True
        self.cancel_timer()
        if ok:
            code = f"{random.randint(0, 999999):06d}"
            events.publish("payment", "Mock charge approved", {"last4": self.last4, "code": code}, self.call.call_sid)
            outcome = success_outcome(balance_for(self.call), self.last4, code)
        else:
            outcome = failure_outcome()
        await self.ws.send_json({"type": "end", "handoffData": json.dumps({"outcome": outcome, "success": ok})})


@router.websocket("/ws/pay")
async def relay_pay_socket(ws: WebSocket) -> None:
    """ConversationRelay WebSocket for payment capture."""
    await ws.accept()
    session: RelayPaySession | None = None
    try:
        while True:
            message = await ws.receive_json()
            kind = message.get("type")
            if kind == "setup":
                call = get_call(message["callSid"])
                session = RelayPaySession(call, get_config().relay_pay, ws)
                session.arm(session.cfg.no_input_seconds)
                events.publish("call", "Payment socket connected", call_sid=call.call_sid)
            elif session and kind == "prompt":
                await session.on_text(message.get("voicePrompt", ""))
            elif session and kind == "dtmf":
                await session.on_dtmf(message.get("digit", ""))
    except WebSocketDisconnect:
        pass
    finally:
        if session:
            session.cancel_timer()


@router.post("/relay-pay/done")
async def relay_pay_done(request: Request) -> Response:
    """<Connect> action after the payment socket ends: returns the caller to the agent."""
    form = {k: str(v) for k, v in (await request.form()).items()}
    handoff = form.get("HandoffData")
    if not handoff:
        return Response(status_code=204)
    call = get_call(form["CallSid"])
    return xml(await return_to_agent_twiml(call, json.loads(handoff)["outcome"]))
