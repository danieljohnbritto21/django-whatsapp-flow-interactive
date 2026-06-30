from __future__ import annotations

from django.conf import settings
from typing import Any
from whatsapp_app.messages import MESSAGES

from whatsapp_app.whatsapp_service import whatsapp_service


def _get_message(key: str, lang: str) -> str:
    """Helper to get a message string in the correct language."""
    return MESSAGES.get(lang, MESSAGES["en"]).get(key, key)


def send_menu(phone_number: str, lang: str = "en") -> Any:
    """Sends the main menu in the specified language."""
    body_text = _get_message("main_menu_body", lang)
    buttons = [
        {"type": "reply", "reply": {"id": "donate", "title": _get_message("donate_button", lang)}},
        {"type": "reply", "reply": {"id": "contact", "title": _get_message("contact_button", lang)}},
        {"type": "reply", "reply": {"id": "location", "title": _get_message("location_button", lang)}},
    ]
    header_text = _get_message("main_menu_header", lang)
    return whatsapp_service.send_interactive_buttons(phone_number, body_text, buttons, header_text=header_text)


def send_contact(phone_number: str, lang: str = "en") -> Any:
    """Sends a native WhatsApp contact card."""
    org_details = settings.THAAGAM_FOUNDATION
    body_text = _get_message("contact_body", lang)
    buttons = [
        {"type": "reply", "reply": {"id": "menu", "title": _get_message("menu_button", lang)}}
    ]
    return whatsapp_service.send_interactive_buttons(
        phone_number, body_text, buttons, header_text=_get_message("contact_header", lang)
    )


def send_location(phone_number: str, lang: str = "en") -> Any:
    """Sends a native WhatsApp location message."""
    # These should be in your settings or a model
    location_details = {
        "latitude": 13.0475,  # Example latitude for Chennai
        "longitude": 80.2088, # Example longitude for Chennai
        "name": "Thaagam Foundation",
        "address": "123, Main Street, Chennai, Tamil Nadu – 600001, India",
    }
    return whatsapp_service.send_location(
        phone_number,
        latitude=location_details["latitude"],
        longitude=location_details["longitude"],
        name=location_details["name"],
        address=location_details["address"],
    )


def send_location_request(phone_number: str, lang: str = "en") -> Any:
    """Sends a native WhatsApp location request message."""
    body_text = _get_message("location_request_body", lang)
    return whatsapp_service.send_location_request(
        phone_number,
        body_text
    )


def send_donate_category_menu(phone_number: str, lang: str = "en") -> Any:
    body_text = _get_message("donate_category_body", lang)
    buttons = [
        {"type": "reply", "reply": {"id": "donate_food", "title": _get_message("food_category", lang)}},
        {"type": "reply", "reply": {"id": "donate_education", "title": _get_message("education_category", lang)}},
        {"type": "reply", "reply": {"id": "donate_medical", "title": _get_message("medical_category", lang)}},
    ]
    return whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text=_get_message("donate_category_header", lang),
    )


def send_payment_cta(phone_number: str, review_text: str) -> Any:
    """Send an interactive button that asks user to open Pay Now.

    Note: the actual URL open happens on the client side via CTA URL.
    We keep this function simple and send a regular reply button.
    """

    buttons = [{"type": "reply", "reply": {"id": "pay_now", "title": "💳 Pay Now"}}]
    body_text = review_text + "\n\nClick *Pay Now* to proceed."
    return whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text="✅ Payment",
    )
