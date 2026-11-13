from typing import Any

from twilio.twiml.voice_response import VoiceResponse

from server.card_parse import expected_length
from server.config import GatherPayConfig, PayVerbConfig, RelayPayConfig
from server.settings import public_url, public_wss, settings

GATHER_FIELDS = ["card", "expiry", "cvv", "zip"]


def build_pay_twiml(cfg: PayVerbConfig, amount: float) -> str:
    """Renders <Pay> TwiML from the scenario 1 config. Omits chargeAmount when tokenizing."""
    attrs: dict[str, Any] = {
        "input": "dtmf",
        "action": public_url("/pay/action"),
        "status_callback": public_url("/pay/status"),
        "payment_connector": cfg.payment_connector or settings.pay_connector,
        "payment_method": cfg.payment_method,
        "token_type": cfg.token_type,
        "currency": cfg.currency,
        "description": cfg.description,
        "language": cfg.language,
        "max_attempts": cfg.max_attempts,
        "timeout": cfg.timeout,
    }
    if cfg.charge:
        attrs["charge_amount"] = f"{amount:.2f}"
    if cfg.payment_method == "credit-card":
        attrs.update(valid_card_types=cfg.valid_card_types, security_code=cfg.security_code, postal_code=cfg.postal_code)
        if cfg.postal_code:
            attrs["min_postal_code_length"] = cfg.min_postal_code_length
    else:
        attrs["bank_account_type"] = cfg.bank_account_type
    response = VoiceResponse()
    pay = response.pay(**attrs)
    for p in cfg.prompts:
        says = [s.strip() for s in p.says if s.strip()]
        if not says:
            continue
        prompt = pay.prompt(
            for_=p.field,
            error_type=p.error_type.strip() or None,
            attempt=p.attempt.strip() or None,
            card_type=p.card_type.strip() or None,
            require_matching_inputs=True if p.require_matching_inputs else None,
        )
        for say in says:
            prompt.say(say)
    return str(response)


def say_voice() -> str | None:
    """<Say> voice matching the agent's ElevenLabs voice, as ElevenLabs.{voiceId}, or None when the agent uses another provider."""
    if settings.tts_provider.lower() == "elevenlabs" and settings.voice:
        return f"ElevenLabs.{settings.voice.split('-')[0]}"
    return None


def build_gather_twiml(cfg: GatherPayConfig, field: str, attempt: int, brand: str | None = None, prefix: str = "") -> str:
    """Renders one speech+DTMF <Gather> step for a card field."""
    fc = cfg.fields[field]
    attrs: dict[str, Any] = {
        "input": "speech dtmf",
        "action": public_url(f"/gather/result?field={field}&attempt={attempt}"),
        "method": "POST",
        "hints": fc.hints,
        "speech_model": cfg.speech_model,
        "speech_timeout": cfg.speech_timeout,
        "timeout": cfg.timeout,
        "finish_on_key": cfg.finish_on_key,
        "action_on_empty_result": True,
    }
    if cfg.enhanced and cfg.speech_model == "phone_call":
        attrs["enhanced"] = True
    if field != "card":
        attrs["num_digits"] = expected_length(field, brand)
    response = VoiceResponse()
    gather = response.gather(**attrs)
    voice = say_voice()
    gather.say(f"{prefix} {fc.prompt}".strip(), **({"voice": voice} if voice else {}))
    return str(response)


def build_relay_pay_twiml(cfg: RelayPayConfig) -> str:
    """Renders <Connect><ConversationRelay> pointing at the payment parser socket."""
    attrs = {
        "url": public_wss("/ws/pay"),
        "transcription_provider": cfg.transcription_provider,
        "speech_model": cfg.speech_model,
        "tts_provider": cfg.tts_provider,
        "voice": cfg.voice,
        "hints": cfg.hints,
        "dtmf_detection": True,
        "welcome_greeting": cfg.prompts["card"],
    }
    response = VoiceResponse()
    connect = response.connect(action=public_url("/relay-pay/done"))
    connect.conversation_relay(**{k: v for k, v in attrs.items() if v not in (None, "")})
    return str(response)
