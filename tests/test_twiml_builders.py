from server.config import GatherPayConfig, PayPrompt, PayVerbConfig, RelayPayConfig
from server.twiml_builders import build_gather_twiml, build_pay_twiml, build_relay_pay_twiml


def test_pay_twiml_charge_and_prompts():
    cfg = PayVerbConfig(prompts=[PayPrompt(field="payment-card-number", error_type="timeout", says=["Enter your card.", " "])])
    xml = build_pay_twiml(cfg, 87.42)
    assert 'chargeAmount="87.42"' in xml
    assert 'action="https://example.ngrok.app/pay/action"' in xml
    assert '<Prompt errorType="timeout" for="payment-card-number"><Say>Enter your card.</Say></Prompt>' in xml


def test_pay_twiml_tokenize_and_ach():
    xml = build_pay_twiml(PayVerbConfig(charge=False, payment_method="ach-debit"), 50)
    assert "chargeAmount" not in xml
    assert 'paymentMethod="ach-debit"' in xml and "bankAccountType" in xml


def test_gather_twiml():
    card = build_gather_twiml(GatherPayConfig(), "card", 1)
    assert 'input="speech dtmf"' in card and "$OOV_CLASS_DIGIT_SEQUENCE" in card and "numDigits" not in card
    assert "field=card&amp;attempt=1" in card
    cvv = build_gather_twiml(GatherPayConfig(), "cvv", 2, brand="amex", prefix="Try again.")
    assert 'numDigits="4"' in cvv and ">Try again. " in cvv


def test_relay_pay_twiml():
    xml = build_relay_pay_twiml(RelayPayConfig())
    assert 'url="wss://example.ngrok.app/ws/pay"' in xml
    assert 'dtmfDetection="true"' in xml and 'transcriptionProvider="Deepgram"' in xml
    assert 'action="https://example.ngrok.app/relay-pay/done"' in xml
