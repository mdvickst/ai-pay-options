import asyncio
from typing import Any

from twilio.rest import Client

from server.settings import settings

client = Client(settings.api_key, settings.api_secret, settings.account_sid)


async def update_call(call_sid: str, **kwargs: Any) -> None:
    """Updates a live call (redirect `url` or inline `twiml`) off the event loop."""
    await asyncio.to_thread(lambda: client.calls(call_sid).update(**kwargs))
