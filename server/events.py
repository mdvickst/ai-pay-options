import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

_subscribers: set[asyncio.Queue] = set()
_backlog: list[dict[str, Any]] = []


def publish(kind: str, title: str, data: dict[str, Any] | None = None, call_sid: str | None = None) -> None:
    """Sends an event to every connected UI feed. `kind` is one of call, transcript, agent, tool, payment, twiml, error."""
    event = {"ts": time.time(), "kind": kind, "title": title, "data": data or {}, "callSid": call_sid}
    _backlog.append(event)
    del _backlog[:-200]
    for queue in list(_subscribers):
        queue.put_nowait(event)


async def stream() -> AsyncIterator[str]:
    """Yields Server-Sent Event frames: the recent backlog, then live events."""
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.add(queue)
    try:
        for event in list(_backlog):
            yield f"data: {json.dumps(event)}\n\n"
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        _subscribers.discard(queue)
