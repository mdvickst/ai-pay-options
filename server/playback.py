import asyncio
import json
import time
from typing import Any

from server import events
from server.state import CallState, get_call

AGENT_SOCKET_PATH = "/ws"


def _value_off(value: Any) -> bool:
    return str(value).strip().lower() in ("off", "false", "0", "stopped", "ended")


def handle_relay_message(call_sid: str, message: dict) -> None:
    """Records ConversationRelay speaker and tokens-played events for a call."""
    name = message.get("name") or message.get("event") or ""
    if message.get("type") != "info" or name not in ("agentSpeaking", "tokensPlayed"):
        return
    call = get_call(call_sid)
    if name == "agentSpeaking":
        call.agent_speaking = not _value_off(message.get("value"))
        if not call.agent_speaking:
            call.agent_off_at = time.monotonic()
            call.playback_changed.set()
    events.publish("call", f"Relay {name}", {"value": message.get("value")}, call_sid)


async def wait_for_playback_end(call: CallState, timeout: float) -> bool:
    """Waits until the agent finishes speaking everything sent so far; returns False if the timeout passed first."""
    async with call.turn_lock:
        sent_at = time.monotonic()
    deadline = sent_at + timeout
    while call.agent_off_at < sent_at:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or call.ended:
            return False
        call.playback_changed.clear()
        try:
            await asyncio.wait_for(call.playback_changed.wait(), remaining)
        except asyncio.TimeoutError:
            return False
    return True


class RelayEventTap:
    """ASGI middleware that reads ConversationRelay info messages on the agent WebSocket, which TAC does not dispatch."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "websocket" or scope.get("path") != AGENT_SOCKET_PATH:
            await self.app(scope, receive, send)
            return
        state = {"call_sid": ""}

        async def tapped_receive() -> dict:
            message = await receive()
            text = message.get("text") if message["type"] == "websocket.receive" else None
            if text:
                try:
                    data = json.loads(text)
                except ValueError:
                    return message
                if data.get("type") == "setup":
                    state["call_sid"] = data.get("callSid", "")
                elif state["call_sid"]:
                    handle_relay_message(state["call_sid"], data)
            return message

        await self.app(scope, tapped_receive, send)
