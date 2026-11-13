import asyncio
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallState:
    """Per-call demo state keyed by CallSid."""

    call_sid: str
    caller_number: str = "unknown"
    balance: float | None = None
    history: list[Any] = field(default_factory=list)
    payment_sid: str | None = None
    payment_field: str | None = None
    no_input_task: asyncio.Task | None = None
    no_input_count: int = 0
    pay_data: dict[str, Any] = field(default_factory=dict)
    turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    ended: bool = False
    agent_speaking: bool = False
    agent_off_at: float = 0.0
    playback_changed: asyncio.Event = field(default_factory=asyncio.Event)


calls: dict[str, CallState] = {}


def get_call(call_sid: str) -> CallState:
    """Returns the state for a call, creating it on first use."""
    if call_sid not in calls:
        calls[call_sid] = CallState(call_sid=call_sid)
    return calls[call_sid]


def balance_for(call: CallState) -> float:
    """Returns the caller's balance: a random amount between 50 and 150, fixed for the call."""
    if call.balance is None:
        call.balance = round(random.uniform(50, 150), 2)
    return call.balance


def end_call_state(call_sid: str) -> None:
    """Drops state for a finished call and cancels its timers."""
    call = calls.pop(call_sid, None)
    if call:
        call.ended = True
        call.payment_sid, call.payment_field = None, None
        if call.no_input_task:
            call.no_input_task.cancel()
