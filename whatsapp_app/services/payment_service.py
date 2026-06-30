from __future__ import annotations

import logging
from decimal import Decimal
from django.conf import settings
from whatsapp_app.messages import MESSAGES
from whatsapp_app.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)


def send_pay_now_cta(phone_number: str, donation_reference: str, amount: Decimal, lang: str = "en", payment_url: str = None) -> None:
    """
    Send a CTA URL interactive button that opens the fixed Thaagam pay page.
    This now uses the centralized whatsapp_service.
    """
    try:
        # Guard against missing or invalid amount/reference
        if not amount or not isinstance(amount, Decimal) or amount <= 0:
            logger.error(f"send_pay_now_cta: Invalid amount '{amount}' for {phone_number}.")
            raise ValueError("Invalid amount for payment link.")
        if not donation_reference:
            logger.error(f"send_pay_now_cta: Missing donation_reference for {phone_number}.")
            raise ValueError("Missing reference for payment link.")

        body_text = MESSAGES.get(lang, MESSAGES["en"]).get("payment_cta_body", "").format(amount=amount)
        button_text = MESSAGES.get(lang, MESSAGES["en"]).get("pay_now_button", "Pay Now")
        header_text = MESSAGES.get(lang, MESSAGES["en"]).get("payment_cta_header", "Complete Your Payment")
        url = payment_url or settings.THAAGAM_PAY_NOW_URL

        whatsapp_service.send_interactive_cta_url(
            to_phone_number=phone_number,
            body_text=body_text,
            button_text=button_text,
            url=url,
            header_text=header_text,
        )
    except Exception as e:
        logger.exception(f"CRITICAL: Failed to send Pay Now CTA to {phone_number} for donation {donation_reference}. Error: {e}")
        # Send a fallback message to the user so they are not left hanging.
        whatsapp_service.send_text_message(phone_number, "We're sorry, but there was an error generating the payment button. Please contact our support team.")
