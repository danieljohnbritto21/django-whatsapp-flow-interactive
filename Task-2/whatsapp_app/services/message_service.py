from __future__ import annotations

from typing import Any

from whatsapp_app.whatsapp_service import whatsapp_service


def send_menu(phone_number: str) -> Any:
    return whatsapp_service.send_main_menu(phone_number)


def send_contact(phone_number: str) -> Any:
    body_text = (
        "📞 *Contact Thaagam Foundation*\n\n"
        "📱 Phone: +91 93456 55206\n"
        "✉️ Email: foundation@thaagam.org\n"
        "🌐 Website: https://thaagam.org"
    )
    buttons = [{"type": "reply", "reply": {"id": "menu", "title": "🔙 Main Menu"}}]
    return whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text="📞 Contact Us",
    )


def send_location(phone_number: str) -> Any:
    body_text = (
        "📍 *Thaagam Foundation – Registered Office*\n\n"
        "🏢 Thaagam Foundation\n"
        "123, Main Street,\n"
        "Chennai, Tamil Nadu – 600001,\n"
        "India"
    )
    buttons = [{"type": "reply", "reply": {"id": "menu", "title": "🔙 Main Menu"}}]
    return whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text="📍 Our Location",
    )


def send_donate_category_menu(phone_number: str) -> Any:
    body_text = "🙏 *Choose a Donation Cause:*\n\nPlease select a donation category."
    buttons = [
        {"type": "reply", "reply": {"id": "donate_food", "title": "🍛 Food"}},
        {"type": "reply", "reply": {"id": "donate_education", "title": "🎓 Education"}},
        {"type": "reply", "reply": {"id": "donate_medical", "title": "🏥 Medical"}},
    ]
    return whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text="❤️ Choose Donation Category",
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

