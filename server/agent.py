import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from agents import (
    Agent,
    ModelSettings,
    RunContextWrapper,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse

from server import events
from server.config import get_config
from server.logs import dump, llm_log
from server.settings import settings
from server.state import CallState, balance_for, get_call
from server.tac_app import voice_channel

set_default_openai_client(AsyncOpenAI(api_key=settings.litellm_api_key, base_url=settings.litellm_base_url or None), use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(True)

GREETING = "[warmly] Thanks for calling ACME Inc. [whispering] This is Ava. [excited curious] How can I help you today?"

BASE_INSTRUCTIONS = """You are Ava, a friendly customer service agent for ACME Inc., speaking with a caller on the phone.
This is ACME's official, PCI-compliant billing line. Card details are entered on the caller's keypad and captured by Twilio's secure payment system; you never see or handle them.
Speak in short, natural sentences. Never use markdown, lists, symbols, or emojis; everything you say is read aloud.
Say dollar amounts naturally, for example "eighty seven dollars and forty two cents".
You can look up the caller's account balance with lookup_balance. Always call it before quoting a balance.
You can take a payment for the full balance. When the caller wants to pay, confirm the amount, then call start_payment.
Never ask the caller to read card details to you, and never repeat card numbers back.
Messages that start with [SYSTEM EVENT] or [PAYMENT EVENT] come from ACME's systems, not the caller. Act on them and never read them aloud. Never write event text yourself; only the system sends events."""

PAYMENTS_API_INSTRUCTIONS = """
In this call the payment is taken on the caller's keypad. ACME's system runs the keypad steps and speaks every keypad prompt itself:
- When the caller agrees to pay, call start_payment and say nothing else that turn.
- While a payment is in progress, caller messages start with a [PAYMENT STATE] line describing which field the keypad is waiting for. You only step in when the caller says something.
- Answer questions in one short sentence. Then call repeat_prompt so the keypad prompt plays again, unless the caller wants to stop.
- If the caller says they typed something wrong, call recapture_field for that field.
- If the caller wants to stop, call cancel_payment and confirm nothing was charged.
- Call get_payment_progress only if the caller asks how far along they are.
- Never read keypad prompts yourself and never announce payment results; the system does both."""


@function_tool
async def lookup_balance(ctx: RunContextWrapper[CallState]) -> dict:
    """Look up the caller's current ACME account balance using their phone number."""
    call = ctx.context
    amount = balance_for(call)
    events.publish("tool", "lookup_balance", {"callerNumber": call.caller_number, "balance": amount}, call.call_sid)
    return {"caller_number": call.caller_number, "balance": amount, "currency": "USD"}


@function_tool
async def start_payment(ctx: RunContextWrapper[CallState]) -> str:
    """Start collecting a card payment for the caller's full balance. Call only after the caller agrees to pay."""
    from server.scenarios import dispatch_start

    return await dispatch_start(ctx.context)


def build_agent(scenario: str) -> Agent[CallState]:
    """Builds the ACME agent with the tools for the active scenario."""
    tools = [lookup_balance, start_payment]
    instructions = BASE_INSTRUCTIONS
    if scenario == "payments_api":
        from server.scenarios.payments_api import TOOLS

        tools += TOOLS
        instructions += PAYMENTS_API_INSTRUCTIONS
    model_settings = ModelSettings(extra_body={"thinking": {"type": "disabled"}}) if "claude" in settings.llm_model else ModelSettings()
    return Agent[CallState](name="ACME Agent", instructions=instructions, tools=tools, model=settings.llm_model, model_settings=model_settings)


EVENT_MARKERS = ("[PAYMENT EVENT", "[SYSTEM EVENT")


class EventTextFilter:
    """Streams text through, dropping everything from the first [PAYMENT EVENT or [SYSTEM EVENT marker onward."""

    def __init__(self) -> None:
        self.pending = ""
        self.muted = False

    def feed(self, delta: str) -> str:
        """Returns the part of the delta that is safe to speak now."""
        if self.muted:
            return ""
        self.pending += delta
        start = self.pending.find("[")
        if start == -1:
            out, self.pending = self.pending, ""
            return out
        tail = self.pending[start:]
        if any(tail.startswith(m) for m in EVENT_MARKERS):
            self.muted = True
            out, self.pending = self.pending[:start], ""
            return out
        if any(m.startswith(tail) for m in EVENT_MARKERS):
            out, self.pending = self.pending[:start], tail
            return out
        out, self.pending = self.pending, ""
        return out

    def flush(self) -> str:
        """Returns any held text once the stream ends."""
        out, self.pending = ("" if self.muted else self.pending), ""
        return out


async def say(call: CallState, text: str) -> None:
    """Speaks a fixed line to the caller, after any running turn, and records it in history."""
    if call.ended:
        return
    async with call.turn_lock:
        if call.ended:
            return

        async def tokens() -> AsyncGenerator[str, None]:
            yield text

        call.history = call.history + [{"role": "assistant", "content": text}]
        events.publish("agent", text, call_sid=call.call_sid)
        await voice_channel.send_response(call.call_sid, tokens())


async def run_turn(call: CallState, text: str) -> None:
    """Runs one agent turn for the call, one at a time per call, and streams the reply over the main ConversationRelay socket."""
    if call.ended:
        return
    async with call.turn_lock:
        if call.ended:
            return
        await _run_turn(call, text)


FALLBACK_LINE = "Sorry, I ran into a problem on my end. Could you say that again?"


def is_policy_error(exc: BaseException) -> bool:
    """True when the LLM provider rejected the prompt under its usage policy."""
    text = f"{type(exc).__name__} {exc}"
    return "ContentPolicyViolation" in text or "flagged as potentially violating" in text


def _items(result: Any) -> list[Any]:
    return [item.to_input_item() for item in result.new_items]


async def _run_turn(call: CallState, text: str) -> None:
    agent = build_agent(get_config().scenario)
    user = {"role": "user", "content": text}

    async def attempt(turn_input: list[Any], spoken: list[str], holder: dict[str, Any]) -> AsyncGenerator[str, None]:
        llm_log.info("call=%s prompt instructions=%s input=%s", call.call_sid, dump(agent.instructions), dump(turn_input))
        result = Runner.run_streamed(agent, turn_input, context=call)
        holder["result"] = result
        speech = EventTextFilter()
        async for event in result.stream_events():
            if event.type == "raw_response_event" and getattr(event.data, "type", "") == "response.output_text.delta":
                out = speech.feed(event.data.delta)
                if out:
                    spoken.append(out)
                    yield out
            elif event.type == "run_item_stream_event" and event.name == "tool_called":
                raw = event.item.raw_item
                events.publish("tool", f"→ {getattr(raw, 'name', 'tool')}", {"arguments": getattr(raw, "arguments", "")}, call.call_sid)
        out = speech.flush()
        if out:
            spoken.append(out)
            yield out
        llm_log.info("call=%s response items=%s", call.call_sid, dump(_items(result)))

    async def tokens() -> AsyncGenerator[str, None]:
        spoken: list[str] = []
        holder: dict[str, Any] = {}
        before = list(call.history)
        try:
            async for out in attempt(call.history + [user], spoken, holder):
                yield out
            call.history = holder["result"].to_input_list()
        except (GeneratorExit, asyncio.CancelledError):
            partial = _items(holder["result"]) if "result" in holder else []
            call.history = before + [user] + partial + ([{"role": "assistant", "content": "".join(spoken)}] if spoken else [])
            llm_log.info("call=%s turn interrupted after %d chars", call.call_sid, len("".join(spoken)))
            raise
        except Exception as exc:
            partial = _items(holder["result"]) if "result" in holder else []
            llm_log.error("call=%s LLM error: %s partial_items=%s", call.call_sid, exc, dump(partial))
            events.publish("error", "LLM request failed", {"error": str(exc)[:300], "policy": is_policy_error(exc)}, call.call_sid)
            retried = False
            if is_policy_error(exc) and not spoken:
                retry: dict[str, Any] = {}
                try:
                    async for out in attempt([user] + partial, spoken, retry):
                        yield out
                    call.history = call.history + retry["result"].to_input_list()
                    retried = True
                    events.publish("agent", "Recovered from content policy error with a minimal prompt", call_sid=call.call_sid)
                except Exception as retry_exc:
                    llm_log.error("call=%s LLM retry failed: %s", call.call_sid, retry_exc)
            if not retried:
                if not spoken:
                    spoken.append(FALLBACK_LINE)
                    yield FALLBACK_LINE
                call.history = call.history + [user, {"role": "assistant", "content": "".join(spoken)}]
        if spoken:
            events.publish("agent", "".join(spoken).strip(), call_sid=call.call_sid)

    await voice_channel.send_response(call.call_sid, tokens())


async def handle_message_ready(user_message: str, context: ConversationSession, memory: TACMemoryResponse | None) -> None:
    """TAC callback for each caller utterance on the main agent socket."""
    call = get_call(context.call_sid or context.conversation_id)
    events.publish("transcript", user_message, call_sid=call.call_sid)
    if not call.payment_sid or get_config().scenario != "payments_api":
        await run_turn(call, user_message)
        return
    from server.scenarios.payments_api import arm_no_input, cancel_no_input, payment_state_note

    cancel_no_input(call)
    try:
        await run_turn(call, f"{payment_state_note(call)}\nCaller said: {user_message}")
    finally:
        if call.payment_field and call.no_input_task is None:
            arm_no_input(call)
