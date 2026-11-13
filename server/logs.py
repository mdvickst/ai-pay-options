import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"))
_root = logging.getLogger("acme")
_root.addHandler(_handler)
_root.setLevel(logging.INFO)
_root.propagate = False

llm_log = logging.getLogger("acme.llm")
ws_log = logging.getLogger("acme.ws")
pay_log = logging.getLogger("acme.pay_connector")


def flag(name: str, default: bool = True) -> bool:
    """Reads an on/off environment variable; accepts 1/0, true/false, on/off, yes/no."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "on", "yes")


for _logger, _env in ((llm_log, "LOG_LLM"), (ws_log, "LOG_WS"), (pay_log, "LOG_PAY_CONNECTOR")):
    _logger.setLevel(logging.INFO if flag(_env) else logging.WARNING)


def dump(value: Any) -> str:
    """Serializes a value to compact JSON for log lines."""
    return json.dumps(value, default=lambda o: getattr(o, "model_dump", lambda: str(o))(), ensure_ascii=False)


class WebSocketLogMiddleware:
    """ASGI middleware that logs every text frame received and sent on WebSocket connections."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "websocket":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if not ws_log.isEnabledFor(logging.INFO):
            await self.app(scope, receive, send)
            return

        async def logged_receive() -> dict:
            message = await receive()
            if message["type"] == "websocket.receive" and message.get("text"):
                ws_log.info("%s <- %s", path, message["text"])
            return message

        async def logged_send(message: dict) -> None:
            if message["type"] == "websocket.send" and message.get("text"):
                ws_log.info("%s -> %s", path, message["text"])
            await send(message)

        await self.app(scope, logged_receive, logged_send)
