import asyncio

import server.agent as agent
import server.scenarios.payments_api as pa
from server.config import PaymentsApiConfig, get_config
from server.state import CallState


def test_next_field_and_lines():
    cfg = PaymentsApiConfig()
    assert pa.next_field(cfg, "expiration-date,security-code,postal-code") == "expiration-date"
    assert pa.next_field(cfg, "") is None
    call = CallState(call_sid="CA1", balance=87.42)
    assert "ch_" not in pa.result_line(call, {"Result": "success", "PaymentConfirmationCode": "ch_123456"})
    assert "declined" in pa.result_line(call, {"Result": "payment-connector-error", "PaymentError": "Card was declined"})
    assert "I got 15 digits" in pa.error_line("invalid-card-number", "payment-card-number", 15)


def test_server_drives_sequence(monkeypatch):
    spoken, updates = [], []

    async def fake_update(call, **kw):
        updates.append(kw)

    async def fake_say(call, text):
        spoken.append(text)

    async def fake_turn(call, text):
        spoken.append(f"LLM:{text[:40]}")

    monkeypatch.setattr(pa, "_update", fake_update)
    monkeypatch.setattr(agent, "say", fake_say)
    monkeypatch.setattr(agent, "run_turn", fake_turn)
    get_config().payments_api.max_attempts = 2

    async def flow():
        call = CallState(call_sid="CA2", balance=50.0, payment_sid="PK1")
        call.pay_data = {"digits": {}, "captured": [], "attempts": {}, "no_input": 0, "card_type": ""}
        await pa.capture(call, "payment-card-number")
        await pa.handle_event(call, {"Capture": "payment-card-number", "Required": "expiration-date,security-code,postal-code", "PaymentCardType": "amex"})
        await pa.handle_event(call, {"Capture": "payment-card-number", "Required": "expiration-date"})
        await pa.handle_event(call, {"Capture": "expiration-date", "ErrorType": "invalid-date", "Required": "expiration-date,security-code,postal-code"})
        await pa.handle_event(call, {"Capture": "expiration-date", "Required": "security-code,postal-code"})
        await pa.handle_event(call, {"Capture": "security-code", "Required": "postal-code"})
        await pa.handle_event(call, {"Capture": "postal-code", "Required": ""})
        await pa.handle_event(call, {"Result": "success"})
        pa.cancel_no_input(call)
        return call

    call = asyncio.run(flow())
    assert [u.get("capture") or u.get("status") for u in updates] == [
        "payment-card-number", "expiration-date", "expiration-date", "security-code", "postal-code", "complete"
    ]
    assert pa.AMEX_SECURITY_PROMPT in spoken and "successful" in spoken[-1] and call.payment_sid is None
