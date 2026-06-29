"""
Service for parsing and validating user input from WhatsApp messages,
specifically for the single-step donor information collection.
"""
import re
from decimal import Decimal, InvalidOperation


def validate_name(name: str) -> list[str]:
    """Validate the donor's name."""
    errors = []
    name_stripped = name.strip()
    if not name_stripped or len(name_stripped) < 2:
        errors.append("• Name must contain at least 2 characters.")
    elif len(name_stripped) > 100:
        errors.append("• Name cannot exceed 100 characters.")
    elif not re.match(r"^[a-zA-Z\s]+$", name_stripped):
        errors.append("• Name must contain only letters and spaces.")
    return errors


def validate_email(email: str) -> list[str]:
    """Validate the donor's email address."""
    errors = []
    if not email:
        errors.append("• Email address is required.")
    elif not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        errors.append("• Email address is invalid.")
    return errors


def validate_mobile(mobile: str) -> list[str]:
    """Validate the donor's mobile number (exactly 10 digits)."""
    errors = []
    if not mobile:
        errors.append("• Mobile number is required.")
    else:
        cleaned_mobile = re.sub(r"\D", "", mobile)
        if len(cleaned_mobile) != 10:
            errors.append("• Mobile number must contain exactly 10 digits.")
        elif not cleaned_mobile.isdigit():
            errors.append("• Mobile number must contain only digits.")
    return errors


def validate_quantity(quantity_str: str) -> tuple[int | None, list[str]]:
    """Validate the donation quantity."""
    errors = []
    try:
        quantity = int(quantity_str)
        if not 1 <= quantity <= 1000:
            errors.append("• Quantity must be between 1 and 1000.")
            return None, errors
        return quantity, errors
    except (ValueError, TypeError):
        errors.append("• Quantity must be a whole number.")
        return None, errors


def validate_amount(amount_str: str) -> tuple[Decimal | None, list[str]]:
    """Validate the donation amount."""
    errors = []
    try:
        amount = Decimal(amount_str)
        if not 100 <= amount <= 1000000:
            errors.append("• Donation amount must be between ₹100 and ₹10,00,000.")
            return None, errors
        return amount, errors
    except (InvalidOperation, TypeError):
        errors.append("• Donation amount must be a valid number.")
        return None, errors


def send_validation_errors(phone_number: str, errors: list[str]):
    """Sends a consolidated list of validation errors to the user."""
    from whatsapp_app.whatsapp_service import whatsapp_service

    error_message = "❌ Please correct the following:\n\n" + "\n".join(errors) + "\n\nPlease try again."

    whatsapp_service.send_text_message(phone_number, error_message)