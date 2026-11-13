import re
import warnings
from dataclasses import dataclass, field
from datetime import date

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    from recognizers_number import Culture, recognize_number

MONTHS = {
    name: f"{i:02d}"
    for i, name in enumerate(
        ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"],
        start=1,
    )
}
NUMBER_WORDS = (
    "zero|oh|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    "seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|double|triple"
)
BRAND_LENGTHS = {"amex": {15}, "visa": {13, 16, 19}, "mastercard": {16}, "discover": {16}, "unknown": set(range(13, 20))}
BRAND_NAMES = {"amex": "American Express", "visa": "Visa", "mastercard": "Mastercard", "discover": "Discover", "unknown": "card"}
ERROR_TEXT = {
    "no-input": "Sorry, I didn't catch that.",
    "wrong-length": "That didn't have the right number of digits.",
    "invalid-card-number": "That card number doesn't look valid.",
    "invalid-date": "That expiration date isn't valid.",
    "invalid-security-code": "That security code isn't the right length.",
    "invalid-postal-code": "That zip code should be five digits.",
}


@dataclass
class FieldResult:
    """Outcome of validating one payment field. `info` holds only non-sensitive values."""

    ok: bool
    error: str | None = None
    info: dict = field(default_factory=dict)


LOOKALIKES = str.maketrans({"o": "0", "q": "0", "i": "1", "l": "1", "z": "2", "s": "5", "b": "8"})
LOOKALIKE_TOKEN = re.compile(r"\b[0-9oqilzsb]*\d[0-9oqilzsb]*\b")


def _normalize(text: str, months: bool) -> str:
    t = re.sub(r"[^\w\s]|_", " ", text.lower())
    t = re.sub(r"(?<=\d) +(?=\d)", "", t)
    t = LOOKALIKE_TOKEN.sub(lambda m: m[0].translate(LOOKALIKES), t)
    if months:
        for name, num in MONTHS.items():
            t = re.sub(rf"\b{name}\b", f" {num} ", t)
    t = re.sub(r"\b(double|triple)\s+(\w+)", lambda m: " ".join([m[2]] * (2 if m[1] == "double" else 3)), t)
    return re.sub(r"\b(oh|o)\b", " zero ", t)


def _words_to_digits(text: str) -> list[str]:
    out = []
    for result in recognize_number(text, Culture.English):
        value = (result.resolution or {}).get("value", "")
        if re.fullmatch(r"\d+", value or ""):
            out.append(value)
    return out


def extract_digits(text: str, months: bool = False) -> str:
    """Converts spoken or typed input ("four one one", "4111", "oh seven") into a digit string."""
    out: list[str] = []
    for part in re.split(r"(\d+)", _normalize(text, months)):
        if part.isdigit():
            out.append(part)
        elif part.strip():
            out.extend(_words_to_digits(part))
    return "".join(out)


def card_brand(digits: str) -> str:
    """Returns the card brand inferred from the leading digits."""
    if re.match(r"3[47]", digits):
        return "amex"
    if digits.startswith("4"):
        return "visa"
    if re.match(r"5[1-5]|2[2-7]", digits):
        return "mastercard"
    if re.match(r"6(011|5)", digits):
        return "discover"
    return "unknown"


def luhn_ok(digits: str) -> bool:
    """Returns True if the digit string passes the Luhn checksum."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def expected_length(field: str, brand: str | None = None, digits: str = "") -> int:
    """Returns the digit count that completes a field, given the brand or the card digits so far."""
    if field == "card":
        return 15 if digits.startswith(("34", "37")) else 16
    if field == "expiry":
        return 4
    if field == "cvv":
        return 4 if brand == "amex" else 3
    if field == "zip":
        return 5
    return 0


def _parse_expiry(digits: str) -> tuple[int, int] | None:
    if len(digits) == 3:
        digits = "0" + digits
    if len(digits) == 4:
        month, year = int(digits[:2]), 2000 + int(digits[2:])
    elif len(digits) == 6:
        month, year = int(digits[:2]), int(digits[2:])
    else:
        return None
    today = date.today()
    if not 1 <= month <= 12 or (year, month) < (today.year, today.month):
        return None
    return month, year


def check_field(field: str, digits: str, brand: str | None = None) -> FieldResult:
    """Validates a captured field (card, expiry, cvv, zip)."""
    if not digits:
        return FieldResult(False, "no-input")
    if field == "card":
        found = card_brand(digits)
        if len(digits) not in BRAND_LENGTHS[found]:
            return FieldResult(False, "wrong-length")
        if not luhn_ok(digits):
            return FieldResult(False, "invalid-card-number")
        return FieldResult(True, info={"brand": found, "last4": digits[-4:]})
    if field == "expiry":
        parsed = _parse_expiry(digits)
        if not parsed:
            return FieldResult(False, "invalid-date")
        return FieldResult(True, info={"expiry": f"{parsed[0]:02d}/{parsed[1] % 100:02d}"})
    if field == "cvv":
        if len(digits) != expected_length("cvv", brand):
            return FieldResult(False, "invalid-security-code")
        return FieldResult(True)
    if field == "zip":
        if len(digits) != 5:
            return FieldResult(False, "invalid-postal-code")
        return FieldResult(True, info={"zip": digits})
    raise ValueError(f"unknown field {field}")


def mask(digits: str) -> str:
    """Masks all but the last four digits; strings of four or fewer are fully masked."""
    if len(digits) <= 4:
        return "•" * len(digits)
    return "•" * (len(digits) - 4) + digits[-4:]


def mask_text(text: str) -> str:
    """Masks every digit and spoken number word in free text."""
    text = re.sub(r"\d", "•", text)
    return re.sub(rf"\b({NUMBER_WORDS})\b", "•", text, flags=re.IGNORECASE)


def spaced(value: str) -> str:
    """Spaces characters so TTS reads them one at a time."""
    return " ".join(value)
