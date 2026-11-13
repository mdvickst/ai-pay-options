import base64
import hmac
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from server import events
from server.card_parse import card_brand, luhn_ok, mask
from server.logs import dump, pay_log
from server.settings import settings

router = APIRouter()
DECLINE_CARDS = {"4000000000000002"}
_results: dict[str, dict] = {}


def _authorized(header: str) -> bool:
    expected = "Basic " + base64.b64encode(f"{settings.pay_connector_username}:{settings.pay_connector_password}".encode()).decode()
    return hmac.compare_digest(header, expected)


SENSITIVE_KEYS = ("cardnumber", "cvv", "expiry_month", "expiry_year", "routing_number", "account_number")


def masked_body(body: dict) -> dict:
    """Copy of a connector request body with card and bank fields masked for logging."""
    out = dict(body)
    for key in SENSITIVE_KEYS:
        if out.get(key):
            out[key] = mask(str(out[key])) if key in ("cardnumber", "account_number") else "•" * len(str(out[key]))
    return out


def process(body: dict) -> dict:
    """Mock processor decision for one Generic Pay Connector request; returns the response body Twilio expects."""
    method = body.get("method", "charge")
    id_key = "charge_id" if method == "charge" else "token_id"
    card = str(body.get("cardnumber") or "")
    if card and not luhn_ok(card):
        return {id_key: "", "error_code": "invalid_card", "error_message": "Card number failed validation"}
    if card in DECLINE_CARDS:
        return {id_key: "", "error_code": "card_declined", "error_message": "Card was declined"}
    prefix = "ch" if method == "charge" else "tok"
    return {id_key: f"{prefix}_{uuid.uuid4().hex[:12]}", "error_code": None, "error_message": None}


@router.post("/payresults")
async def payresults(request: Request) -> JSONResponse:
    """Generic Pay Connector endpoint: checks Basic auth, answers idempotently per transaction_id, publishes a masked event."""
    if not _authorized(request.headers.get("authorization", "")):
        events.publish("error", "Pay connector request rejected: bad credentials")
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    pay_log.info("payresults request headers=%s body=%s", dump({k: v for k, v in request.headers.items() if k.lower() != "authorization"}), dump(masked_body(body)))
    txn = str(body.get("transaction_id", ""))
    if txn not in _results:
        _results[txn] = process(body)
    result = _results[txn]
    card = str(body.get("cardnumber") or "")
    events.publish(
        "payment",
        f"Pay connector {body.get('method', 'charge')} request",
        {
            "transaction_id": txn,
            "amount": body.get("amount"),
            "currency": body.get("currency_code"),
            "card": mask(card) if card else None,
            "brand": card_brand(card) if card else None,
            "response": result,
        },
    )
    pay_log.info("payresults response transaction_id=%s body=%s", txn, dump(result))
    return JSONResponse(result)
