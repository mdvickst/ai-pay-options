import importlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from tac.server import TACFastAPIServer

from server import agent, api, pay_connector, voice_routes
from server.logs import WebSocketLogMiddleware
from server.playback import RelayEventTap
from server.tac_app import tac, voice_channel

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
SCENARIO_MODULES: list[str] = ["payments_api", "pay_verb", "gather", "relay_pay"]


def create_server() -> TACFastAPIServer:
    """Builds the TAC server with the demo API, voice, and scenario routes plus the static UI."""
    tac.on_message_ready(agent.handle_message_ready)
    server = TACFastAPIServer(tac=tac, voice_channel=voice_channel, app=FastAPI(title="ACME Pay Options"))
    server.app.add_middleware(WebSocketLogMiddleware)
    server.app.add_middleware(RelayEventTap)
    server.app.include_router(api.router)
    server.app.include_router(voice_routes.router)
    server.app.include_router(pay_connector.router)
    for name in SCENARIO_MODULES:
        server.app.include_router(importlib.import_module(f"server.scenarios.{name}").router)
    if WEB_DIST.exists():
        server.app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return server


if __name__ == "__main__":
    create_server().start()
