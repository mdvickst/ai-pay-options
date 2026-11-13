import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.pay_connector import process, router

app = FastAPI()
app.include_router(router)
client = TestClient(app)
AUTH = {"Authorization": "Basic " + base64.b64encode(b"test:secret").decode()}
CHARGE = {"method": "charge", "transaction_id": "t1", "cardnumber": "4111111111111111", "cvv": "123", "expiry_month": "07", "expiry_year": "2029", "amount": "87.42", "currency_code": "USD"}


def test_process_outcomes():
    assert process(CHARGE)["charge_id"].startswith("ch_")
    assert process({**CHARGE, "method": "tokenize"})["token_id"].startswith("tok_")
    declined = process({**CHARGE, "cardnumber": "4000000000000002"})
    assert declined["error_code"] == "card_declined" and "charge_id" in declined
    assert process({**CHARGE, "cardnumber": "4111111111111112"})["error_code"] == "invalid_card"


def test_route_auth_and_idempotency():
    assert client.post("/payresults", json=CHARGE).status_code == 401
    first = client.post("/payresults", json=CHARGE, headers=AUTH).json()
    again = client.post("/payresults", json=CHARGE, headers=AUTH).json()
    assert first["charge_id"] == again["charge_id"] and first["error_code"] is None
