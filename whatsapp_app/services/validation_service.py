"""
Service for parsing and validating user input from WhatsApp messages,
specifically for the single-step donor information collection.
"""
import re
from whatsapp_app.messages import MESSAGES
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


def validate_email(email: str, lang: str = "en") -> list[str]:
    """Validate the donor's email address."""
    # 5. No Spaces & 8. Normalization
    email = email.strip()
    error_message = MESSAGES.get(lang, MESSAGES["en"]).get("invalid_email", "Please enter a valid email address.")
    
    # 1. Basic Format & 2. Length Limits
    if not email or len(email) > 320:
        return [error_message]

    if email.count('@') != 1:
        return [error_message]

    local_part, domain_part = email.rsplit('@', 1)

    # 2. Length Limits
    if not local_part or len(local_part) > 64 or not domain_part:
        return [error_message]

    # 3. Local Part Rules
    if not re.match(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+$", local_part):
        return [error_message]

    # 4. Dot Rules
    if local_part.startswith('.') or local_part.endswith('.') or '..' in local_part:
        return [error_message]

    # 6. Domain Rules
    if '.' not in domain_part or domain_part.startswith('.') or domain_part.endswith('.') or '..' in domain_part:
        return [error_message]

    domain_labels = domain_part.split('.')
    for label in domain_labels:
        if not label or not re.match(r"^[a-zA-Z0-9-]+$", label):
            return [error_message]
        if label.startswith('-') or label.endswith('-'):
            return [error_message]

    # 7. Top-Level Domain (TLD)
    tld = domain_labels[-1]
    if len(tld) < 2 or not re.match(r"^[a-zA-Z]+$", tld):
        return [error_message]

    return [] # No errors


def validate_mobile(mobile: str, lang: str = "en") -> list[str]:
    """Validate the donor's mobile number (exactly 10 digits)."""
    errors = []
    error_message = MESSAGES.get(lang, MESSAGES["en"]).get("invalid_mobile", "• Mobile number must be 10 digits and start with 6, 7, 8, or 9.")
    if not mobile:
        errors.append("• Mobile number is required.")
    else:
        cleaned_mobile = re.sub(r"\D", "", mobile)
        # Reject if not 10 digits, or starts with 0-5, or all same digits
        if not re.match(r"^[6-9]\d{9}$", cleaned_mobile) or len(set(cleaned_mobile)) == 1:
            errors.append(error_message)
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


def send_validation_errors(phone_number: str, errors: list[str], lang: str = "en"):
    """Sends a consolidated list of validation errors to the user."""
    from whatsapp_app.whatsapp_service import whatsapp_service
    invalid_email_msg = MESSAGES.get(lang, MESSAGES["en"]).get("invalid_email", "Please enter a valid email address.")
    
    # Handle specific email validation message
    if len(errors) == 1 and errors[0] == invalid_email_msg:
        error_message = errors[0]
    else:
        error_message = "❌ Please correct the following:\n\n" + "\n".join(errors) + "\n\nPlease try again."

    whatsapp_service.send_text_message(phone_number, error_message)