import re
from decimal import Decimal, InvalidOperation


PAY_NOW_URL = "https://thaagam.org/referral/qpay/HBSGF/"


def clean_whatsapp_text(text: str) -> str:
    return (text or "").strip()


def safe_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(str(default))


def extract_digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def normalize_command(text: str) -> str:
    return clean_whatsapp_text(text).lower()

