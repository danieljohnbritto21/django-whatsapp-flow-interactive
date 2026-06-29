from __future__ import annotations

from decimal import Decimal
from whatsapp_app.whatsapp_service import whatsapp_service


PAY_NOW_URL = "https://thaagam.org/referral/qpay/HBSGF/"


def send_pay_now_cta(phone_number: str, donation_reference: str, amount: Decimal) -> None:
    """
    Send a CTA URL interactive button that opens the fixed Thaagam pay page.
    This now uses the centralized whatsapp_service.
    """
    body_text = f"Your donation of ₹{amount:,.0f} is ready. Click below to complete the payment."
    
    whatsapp_service.send_interactive_cta_url(
        to_phone_number=phone_number,
        body_text=body_text,
        button_text="Pay Now",
        url=PAY_NOW_URL,
        header_text="💳 Complete Your Payment"
    )
