import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings read from the environment."""

    account_sid: str
    auth_token: str
    api_key: str
    api_secret: str
    twiml_app_sid: str
    phone_number: str
    public_domain: str
    litellm_base_url: str
    litellm_api_key: str
    llm_model: str
    pay_connector: str
    pay_connector_username: str
    pay_connector_password: str
    tts_provider: str
    voice: str
    transcription_provider: str
    speech_model: str


def _load() -> Settings:
    env = os.environ
    return Settings(
        account_sid=env["TWILIO_ACCOUNT_SID"],
        auth_token=env["TWILIO_AUTH_TOKEN"],
        api_key=env["TWILIO_API_KEY"],
        api_secret=env["TWILIO_API_SECRET"],
        twiml_app_sid=env.get("TWILIO_TWIML_APP_SID", ""),
        phone_number=env["TWILIO_PHONE_NUMBER"],
        public_domain=env["TWILIO_VOICE_PUBLIC_DOMAIN"],
        litellm_base_url=env.get("LITELLM_BASE_URL", ""),
        litellm_api_key=env["LITELLM_API_KEY"],
        llm_model=env.get("LLM_MODEL", "claude-haiku-5-5"),
        pay_connector=env.get("PAY_CONNECTOR") or "Default",
        pay_connector_username=env.get("PAY_CONNECTOR_USERNAME", "test"),
        pay_connector_password=env.get("PAY_CONNECTOR_PASSWORD", ""),
        tts_provider=env.get("TTS_PROVIDER", ""),
        voice=env.get("VOICE", ""),
        transcription_provider=env.get("TRANSCRIPTION_PROVIDER", ""),
        speech_model=env.get("SPEECH_MODEL", ""),
    )


settings = _load()


def public_url(path: str) -> str:
    """Returns the public HTTPS URL for a server path."""
    return f"https://{settings.public_domain}{path}"


def public_wss(path: str) -> str:
    """Returns the public WSS URL for a server path."""
    return f"wss://{settings.public_domain}{path}"
