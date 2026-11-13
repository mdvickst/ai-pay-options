import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

Scenario = Literal["pay_verb", "payments_api", "relay_pay", "gather"]
TokenType = Literal["one-time", "reusable", "payment-method"]


class PayPrompt(BaseModel):
    """One <Prompt> inside <Pay>. Empty strings mean the attribute is omitted."""

    field: str = "payment-card-number"
    error_type: str = ""
    attempt: str = ""
    card_type: str = ""
    require_matching_inputs: bool = False
    says: list[str] = Field(default_factory=lambda: [""])


class PayVerbConfig(BaseModel):
    """Scenario 1 <Pay> attributes and prompts."""

    payment_connector: str = ""
    charge: bool = True
    currency: str = "usd"
    token_type: TokenType = "reusable"
    payment_method: Literal["credit-card", "ach-debit"] = "credit-card"
    bank_account_type: Literal["consumer-checking", "consumer-savings", "commercial-checking"] = "consumer-checking"
    valid_card_types: str = "visa mastercard amex"
    max_attempts: int = 2
    timeout: int = 5
    postal_code: bool = True
    min_postal_code_length: int = 5
    security_code: bool = True
    language: str = "en-US"
    description: str = "ACME balance payment"
    prompts: list[PayPrompt] = Field(default_factory=list)


class PaymentsApiConfig(BaseModel):
    """Scenario 2 Payments API session settings and agent prompts per capture field."""

    payment_connector: str = ""
    charge: bool = True
    token_type: TokenType = "reusable"
    valid_card_types: str = "visa mastercard amex"
    postal_code: bool = True
    security_code: bool = True
    timeout: int = 5
    confirmation: bool = False
    max_attempts: int = 2
    no_input_seconds: int = 8
    max_no_input_retries: int = 1
    field_prompts: dict[str, str] = Field(
        default_factory=lambda: {
            "payment-card-number": "Please enter your card number on your keypad, followed by the pound key.",
            "expiration-date": "Now enter the expiration date, two digits for the month and two for the year.",
            "security-code": "Now enter the security code on your card.",
            "postal-code": "Finally, enter your five digit billing zip code.",
        }
    )


class RelayPayConfig(BaseModel):
    """Scenario 3 payment ConversationRelay settings and parser prompts."""

    transcription_provider: Literal["Deepgram", "Google"] = "Deepgram"
    speech_model: str = "nova-3-general"
    tts_provider: str = ""
    voice: str = ""
    hints: str = "credit card, expiration date, security code, zip code"
    max_attempts: int = 3
    settle_seconds: float = 3.0
    no_input_seconds: int = 10
    prompts: dict[str, str] = Field(
        default_factory=lambda: {
            "card": "Please say or key in your card number.",
            "expiry": "Thanks. Now the expiration date, month and year.",
            "cvv": "And the security code.",
            "zip": "Last one, your five digit billing zip code.",
            "confirm": "I have a {brand} ending in {last4}. Say yes or press 1 to pay ${amount}, or say no or press 2 to start over.",
        }
    )


class GatherField(BaseModel):
    """Prompt and speech hints for one <Gather> step."""

    prompt: str
    hints: str


class GatherPayConfig(BaseModel):
    """Scenario 4 <Gather> settings."""

    speech_model: str = "phone_call"
    enhanced: bool = True
    timeout: int = 8
    speech_timeout: str = "5"
    finish_on_key: str = "#"
    max_attempts: int = 3
    show_raw_speech: bool = True
    fields: dict[str, GatherField] = Field(
        default_factory=lambda: {
            "card": GatherField(prompt="Please say or enter your card number, then press pound.", hints="$OOV_CLASS_DIGIT_SEQUENCE"),
            "expiry": GatherField(prompt="Please say or enter the expiration date, month then year.", hints="$MONTH $YEAR $OOV_CLASS_DIGIT_SEQUENCE"),
            "cvv": GatherField(prompt="Please say or enter the security code.", hints="$OOV_CLASS_DIGIT_SEQUENCE"),
            "zip": GatherField(prompt="Please say or enter your billing zip code.", hints="$POSTALCODE $OOV_CLASS_DIGIT_SEQUENCE"),
        }
    )


class DemoConfig(BaseModel):
    """Everything the UI can change. One global instance per server."""

    scenario: Scenario = "pay_verb"
    handoff_delay_seconds: float = 10.0
    pay_verb: PayVerbConfig = Field(default_factory=PayVerbConfig)
    payments_api: PaymentsApiConfig = Field(default_factory=PaymentsApiConfig)
    relay_pay: RelayPayConfig = Field(default_factory=RelayPayConfig)
    gather: GatherPayConfig = Field(default_factory=GatherPayConfig)


CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", Path(__file__).resolve().parent.parent / "data" / "config.json"))


def _load() -> DemoConfig:
    if CONFIG_PATH.exists():
        return DemoConfig.model_validate_json(CONFIG_PATH.read_text())
    return DemoConfig()


_current = _load()


def get_config() -> DemoConfig:
    """Returns the active demo config."""
    return _current


def set_config(cfg: DemoConfig) -> None:
    """Replaces the active demo config and writes it to CONFIG_PATH."""
    global _current
    _current = cfg
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(cfg.model_dump_json(indent=2))
