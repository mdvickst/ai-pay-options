import asyncio
import importlib
from collections.abc import Awaitable, Callable

from server import events
from server.config import get_config
from server.state import CallState

HANDOFF_LINE = (
    "Payment hand-off scheduled. In one short sentence, tell the caller you are transferring them to "
    "ACME's secure payment line now. Say nothing else."
)
_tasks: set[asyncio.Future] = set()


def spawn(coro: Awaitable[None]) -> None:
    """Runs a coroutine in the background and keeps a reference until it finishes."""
    task = asyncio.ensure_future(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def dispatch_start(call: CallState) -> str:
    """Starts the active scenario's payment flow and returns the tool result for the agent."""
    scenario = get_config().scenario
    events.publish("tool", f"start_payment ({scenario})", call_sid=call.call_sid)
    module = importlib.import_module(f"server.scenarios.{scenario}")
    return await module.start(call)


def schedule_redirect(call: CallState, redirect: Callable[[CallState], Awaitable[None]]) -> str:
    """Redirects the call after the agent has spoken its hand-off line; returns the tool result text."""

    async def later() -> None:
        from server.playback import wait_for_playback_end

        finished = await wait_for_playback_end(call, get_config().handoff_delay_seconds)
        events.publish("call", "Hand-off line finished" if finished else "Hand-off wait timed out", call_sid=call.call_sid)
        if call.ended:
            return
        try:
            await redirect(call)
            events.publish("call", "Redirected to payment flow", call_sid=call.call_sid)
        except Exception as exc:
            events.publish("error", "Redirect failed", {"error": str(exc)}, call.call_sid)

    spawn(later())
    return HANDOFF_LINE
