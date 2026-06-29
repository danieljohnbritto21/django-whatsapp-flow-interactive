"""Enhanced handlers for WhatsApp flows.

This module may be imported either as `enhanced_handlers` (when called from
`whatsapp_app.views` via absolute import) or as `whatsapp_app.enhanced_handlers`
(when running within the Django project).

To avoid `attempted relative import with no known parent package` errors,
use absolute imports throughout and do not rely on package-relative imports.
"""

import logging

from whatsapp_app.models import Donation
from whatsapp_app.whatsapp_service import whatsapp_service
from whatsapp_app.views import reset_to_menu

logger = logging.getLogger(__name__)


def handle_food_packages_selection_new(phone_number, session, message_text):
    """Handle interactive package selection"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Package selection received: '{message_text}'")

    data = session.session_data
    donation_id = data.get('donation_id')

    if not donation_id:
        whatsapp_service.send_text_message(phone_number, "❌ Error: Donation not found. Please start over.")
        reset_to_menu(phone_number, session)
        return

    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        whatsapp_service.send_text_message(phone_number, "❌ Error: Donation not found. Please start over.")
        reset_to_menu(phone_number, session)
        return

    selected_package = None
    package_amount = 0

    # Handle package selection by ID (from interactive list)
    if message_text.startswith('pkg_'):
        package_mapping = {
            'pkg_1': {'name': 'Birthday Banner', 'price': 3000},
            'pkg_2': {'name': 'Birthday Wish Video', 'price': 3000},
            'pkg_3': {'name': 'Wish Video with Cake', 'price': 3000},
            'pkg_4': {'name': 'Image on Cake', 'price': 1300},
            'pkg_5': {'name': 'Distribution Video', 'price': 6000},
            'pkg_6': {'name': 'Image on Parcel', 'price': 800}
        }

        if message_text in package_mapping:
            pkg_info = package_mapping[message_text]
            selected_package = pkg_info
            # Convert to Decimal for database
            from decimal import Decimal
            package_price = Decimal(pkg_info['price'])
            package_amount = pkg_info['price']

            # Save package to donation
            from whatsapp_app.models import DonationPackage
            DonationPackage.objects.create(
                donation=donation,
                package_name=pkg_info['name'],
                price=package_price
            )

            # Update donation amount
            donation.amount = donation.amount + package_price
            donation.save()
        else:
            whatsapp_service.send_text_message(phone_number, "❌ Invalid package selection. Please try again.")
            return
    elif message_text.lower() == 'skip_packages':
        # Skip packages - continue without package
        selected_package = None
        package_amount = 0
    else:
        # Try to find by title match (fallback for text input)
        title_to_pkg = {
            'birthday banner': {'name': 'Birthday Banner', 'price': 3000},
            'birthday wish video': {'name': 'Birthday Wish Video', 'price': 3000},
            'wish video with cake': {'name': 'Wish Video with Cake', 'price': 3000},
            'image on cake': {'name': 'Image on Cake', 'price': 1300},
            'distribution video': {'name': 'Distribution Video', 'price': 6000},
            'image on parcel': {'name': 'Image on Parcel', 'price': 800},
            'skip packages': None
        }
        if message_text.lower() in title_to_pkg:
            selected_package = title_to_pkg[message_text.lower()]
            if selected_package:
                package_amount = selected_package['price']
                from decimal import Decimal
                package_price = Decimal(selected_package['price'])
                from whatsapp_app.models import DonationPackage
                DonationPackage.objects.create(
                    donation=donation,
                    package_name=selected_package['name'],
                    price=package_price
                )
                donation.amount = donation.amount + package_price
                donation.save()
        else:
            whatsapp_service.send_text_message(phone_number, "❌ Please select a package from the list above.")
            return

    # Show donation summary and redirect to payment
    redirect_to_thaagam_payment(phone_number, session, donation, selected_package, package_amount)

def redirect_to_thaagam_payment(phone_number, session, donation, selected_package=None, package_amount=0):
    """Show donation summary with CTA URL button for payment"""
    from whatsapp_app.models import DonationItem
    from decimal import Decimal
    import logging
    logger = logging.getLogger(__name__)

    # Build donation summary
    thaagam_url = "https://thaagam.org/referral/qpay/HBSGF/"
    final_amount = donation.amount
    # Convert to int for calculation
    food_amount = int(final_amount) - int(package_amount)

    # Build food items summary
    food_items = DonationItem.objects.filter(donation=donation)
    food_summary = ""
    for item in food_items:
        food_summary += f"{item.item_name} x {item.quantity}\n{int(item.subtotal)}\n\n"

    if not food_summary:
        food_summary = "No items\n"

    # Build package section
    package_section = ""
    if selected_package:
        package_section = f"Extra Package\n{selected_package['name']}\n{package_amount}\n\n"

    # Build donor details
    donor_details = f"Name: {donation.full_name or 'N/A'}\nEmail: {donation.email or 'N/A'}\nWhatsApp: +{donation.whatsapp_phone_number or 'N/A'}\n"

    # Build summary message
    summary_msg = f"Donation Summary\n\nFood Items\n{food_summary}{package_section}Donor Details\n{donor_details}\n--------------------------------\n\nFood Amount: {food_amount}\nPackage Amount: {package_amount}\nGrand Total: {int(final_amount)}\n\nPayment Status: Pending"

    whatsapp_service.send_text_message(phone_number, summary_msg)
    logger.info("Donation Summary sent.")

    # Send CTA URL button for payment - opens browser directly when tapped
    cta_message = f"💳 Complete Your Payment\n\nDonation saved successfully.\n\nGrand Total: ₹{int(final_amount)}\n\nPayment Status: Pending\n\nClick the button below to complete your payment."

    logger.info("Sending Pay Now button...")
    logger.info(f"CTA URL: {thaagam_url}")

    try:
        result = whatsapp_service.send_interactive_cta_url(
            phone_number,
            cta_message,
            "Pay Now",
            thaagam_url
        )
        logger.info(f"Pay Now button sent. Result: {result}")
    except Exception as e:
        logger.error(f"CTA failed: {e}")
        # NO fallback - only CTA button should be sent

    # DO NOT reset to menu - set state to wait for payment
    # Store payment URL in session for later use
    data = session.session_data or {}
    data['payment_url'] = thaagam_url
    data['reference_number'] = donation.reference_number
    session.session_data = data
    logger.info(f"Setting state to FOOD_PAYMENT_REVIEW for {donation.reference_number}")
    session.current_state = 'FOOD_PAYMENT_REVIEW'
    session.save()

    logger.info(f"Donation {donation.reference_number} ready for payment, NOT resetting to menu")

def handle_final_payment_confirmation(phone_number, session, choice):
    """Handle final Pay Now button click"""
    data = session.session_data

    if choice.lower() in ['pay_now', 'final_pay']:
        create_simple_food_donation_with_thaagam(phone_number, session, data)
    else:
        whatsapp_service.send_text_message(
            phone_number,
            "❌ Please click the Pay Now button to complete your donation."
        )

def create_simple_food_donation_with_thaagam(phone_number, session, data):
    """Create food donation with packages and redirect to Thaagam payment URL"""
    try:
        food_item = data['selected_food_item']
        base_amount = data['total_amount']
        package_amount = data.get('package_total', 0)
        final_amount = base_amount + package_amount
        
        # Create donation
        donation = Donation.objects.create(
            whatsapp_phone_number=phone_number,
            category='FOOD',
            cause='FOOD',
            amount=final_amount,
            full_name=data['full_name'],
            mobile_number=data['mobile_number'],
            email=data['email'],
            payment_status='PENDING',
        )
        
        # Create donation item
        from whatsapp_app.models import DonationItem
        DonationItem.objects.create(
            donation=donation,
            item_type='FOOD',
            item_name=food_item['name'],
            item_id=food_item['id'],
            quantity=data['quantity'],
            unit_price=food_item['price'],
            subtotal=base_amount,
        )
        
        # Save selected packages
        from whatsapp_app.models import DonationPackage
        for pkg_data in data.get('selected_packages', []):
            DonationPackage.objects.create(
                donation=donation,
                package_name=pkg_data['name'],
                price=pkg_data['price']
            )
        
        # Send success message with Thaagam payment URL
        thaagam_url = "https://thaagam.org/referral/qpay/HBSGF/"
        
        package_summary = ""
        if data.get('selected_packages'):
            pkg_names = [pkg['name'] for pkg in data['selected_packages']]
            package_summary = f"\n🎁 Packages: {', '.join(pkg_names)}"
        
        message = f"""
🎉 *Donation Created Successfully!*

🔖 *Reference:* {donation.reference_number}
🍽️ *Item:* {food_item['name']}
📦 *Quantity:* {data['quantity']}
💰 *Food Amount:* ₹{base_amount:,.0f}{package_summary}
💵 *Total Amount:* ₹{final_amount:,.0f}

💳 *Complete your payment by clicking the link below:*
{thaagam_url}

Thank you for your generous support! ❤️
        """
        
        whatsapp_service.send_text_message(phone_number, message)
        reset_to_menu(phone_number, session)
        
        logger.info(f"Food donation {donation.reference_number} created with Thaagam redirect")
        
    except Exception as e:
        logger.error(f"Error creating food donation with Thaagam: {str(e)}")
        whatsapp_service.send_text_message(phone_number, "❌ Error creating donation. Please try again.")
        reset_to_menu(phone_number, session)