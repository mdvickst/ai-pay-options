from server.card_parse import check_field, extract_digits, mask, mask_text


def test_extract_spoken_digits():
    words = "four " + "one " * 15
    assert extract_digits(words) == "4" + "1" * 15
    assert extract_digits("4111 1111 1111 1111") == "4111111111111111"
    assert extract_digits("double four five") == "445"
    assert extract_digits("my zip is 9 4 1 0 5.") == "94105"
    assert extract_digits("oh seven twenty eight") == "0728"
    assert extract_digits("July twenty eight", months=True) == "0728"


def test_check_card():
    ok = check_field("card", "4111111111111111")
    assert ok.ok and ok.info == {"brand": "visa", "last4": "1111"}
    assert check_field("card", "4111111111111112").error == "invalid-card-number"
    assert check_field("card", "411111111111").error == "wrong-length"
    assert check_field("card", "").error == "no-input"


def test_check_other_fields():
    assert check_field("expiry", "0799").ok
    assert check_field("expiry", "1399").error == "invalid-date"
    assert check_field("expiry", "0120").error == "invalid-date"
    assert check_field("cvv", "123", "visa").ok
    assert check_field("cvv", "123", "amex").error == "invalid-security-code"
    assert check_field("zip", "94105").ok


def test_masking():
    assert mask("4111111111111111") == "••••••••••••1111"
    masked = mask_text("my card is 4111 one two double three")
    assert not any(c.isdigit() for c in masked)
    for word in ("one", "two", "double", "three"):
        assert word not in masked


def test_extract_digits_strips_punctuation_and_lookalikes():
    assert extract_digits("4O11, 2Z3-l5") == "4011223" + "15"
    assert extract_digits("zip is 9021O.") == "90210"
    assert extract_digits("05/28", months=True) == "0528"
    assert extract_digits("it is 1 2 3") == "123"
