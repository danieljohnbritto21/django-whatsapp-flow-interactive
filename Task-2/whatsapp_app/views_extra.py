import re
from .whatsapp_service import whatsapp_service
from .models import Donation, DonationItem
from decimal import Decimal


def handle_simple_form(phone_number, session, msg_text_raw, category):
    """Handle a simple, multi-step form for collecting donation details."""
    state = session.current_state
    data = session.session_data

    # State machine for the form
    if state.endswith('_QUANTITY'):
        try:
            quantity = int(msg_text_raw)
            if quantity <= 0: raise ValueError
            data['quantity'] = quantity
            item_price = Decimal(data.get('selected_item', {}).get('price', '0'))
            data['amount'] = quantity * item_price
            session.current_state = f'{category}_FORM_NAME'
            session.save()
            whatsapp_service.send_text_message(phone_number, f"✅ Quantity: {quantity}\n\nPlease enter your *Full Name*:")
        except (ValueError, TypeError):
            whatsapp_service.send_text_message(phone_number, "❌ Invalid quantity. Please enter a whole number (e.g., 5).")

    elif state.endswith('_AMOUNT'):
        try:
            amount = Decimal(msg_text_raw)
            if amount < 1: raise ValueError
            data['amount'] = amount
            session.current_state = f'{category}_FORM_NAME'
            session.save()
            whatsapp_service.send_text_message(phone_number, f"✅ Amount: ₹{amount:,.0f}\n\nPlease enter your *Full Name*:")
        except (ValueError, TypeError):
            whatsapp_service.send_text_message(phone_number, "❌ Invalid amount. Please enter a number (e.g., 500).")

    elif state.endswith('_NAME'):
        if len(msg_text_raw) < 2:
            whatsapp_service.send_text_message(phone_number, "❌ Please enter a valid name.")
            return
        data['full_name'] = msg_text_raw
        session.current_state = f'{category}_FORM_EMAIL'
        session.save()
        whatsapp_service.send_text_message(phone_number, f"✅ Name: {msg_text_raw}\n\nPlease enter your *Email Address*:")

    elif state.endswith('_EMAIL'):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", msg_text_raw):
            whatsapp_service.send_text_message(phone_number, "❌ Please enter a valid email address.")
            return
        data['email'] = msg_text_raw
        session.current_state = f'{category}_FORM_PHONE'
        session.save()
        whatsapp_service.send_text_message(phone_number, f"✅ Email: {msg_text_raw}\n\nPlease enter your *Phone Number*:")

    elif state.endswith('_PHONE'):
        phone = re.sub(r'\D', '', msg_text_raw)
        if not (10 <= len(phone) <= 15):
            whatsapp_service.send_text_message(phone_number, "❌ Please enter a valid phone number.")
            return
        data['phone_number'] = phone
        session.current_state = f'{category}_FORM_INSTAGRAM'
        session.save()
        whatsapp_service.send_text_message(phone_number, f"✅ Phone: {phone}\n\nPlease enter your *Instagram ID* (or type 'skip'):")

    elif state.endswith('_INSTAGRAM'):
        data['instagram_id'] = '' if msg_text_raw.lower() == 'skip' else msg_text_raw
        session.current_state = f'{category}_REVIEW'
        session.save()
        show_review_screen(phone_number, session, category)


def show_review_screen(phone_number, session, category):
    """Display the final review screen before payment."""
    data = session.session_data
    selected_item = data.get('selected_item', {})

    review_parts = [
        "📋 *Review Your Donation*",
        f"Category: {category.title()}",
    ]

    if category == 'FOOD':
        review_parts.append(f"Item: {selected_item.get('name', 'N/A')}")
        review_parts.append(f"Quantity: {data.get('quantity', 'N/A')}")
    elif category == 'EDUCATION':
        review_parts.append(f"Student: {selected_item.get('name', 'N/A')}")
    elif category == 'MEDICAL':
        review_parts.append(f"Patient: {selected_item.get('name', 'N/A')}")

    review_parts.extend([
        f"Amount: ₹{data.get('amount', 0):,.0f}",
        "---",
        f"Name: {data.get('full_name', 'N/A')}",
        f"Email: {data.get('email', 'N/A')}",
        f"Phone: {data.get('phone_number', 'N/A')}",
    ])

    body_text = "\n".join(review_parts)
    buttons = [
        {'type': 'reply', 'reply': {'id': 'proceed_payment', 'title': '💳 Proceed to Payment'}},
        {'type': 'reply', 'reply': {'id': 'edit_donation', 'title': '✏️ Edit'}},
    ]
    whatsapp_service.send_interactive_buttons(phone_number, body_text, buttons, header_text="Confirm Details")


def handle_edit_donation(phone_number, session, category):
    """Handle the 'Edit' button click on the review screen."""
    session.current_state = f"{category}_FORM_QUANTITY" if category == 'FOOD' else f"{category}_FORM_AMOUNT"
    session.session_data.pop('full_name', None)
    session.session_data.pop('email', None)
    session.session_data.pop('phone_number', None)
    session.session_data.pop('instagram_id', None)
    session.save()
    whatsapp_service.send_text_message(phone_number, "✏️ Let's start over with the details for this donation. Please re-enter the amount/quantity.")