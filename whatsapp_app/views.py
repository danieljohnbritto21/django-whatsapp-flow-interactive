import json
import logging
import re
import os
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

logger = logging.getLogger(__name__)

# =============================================
# DEBUG ENDPOINT
# =============================================

@csrf_exempt
def debug_webhook(request):
    """Ultra simple debug endpoint"""
    print("=" * 60)
    print("🚨 DEBUG WEBHOOK CALLED!")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"Content-Type: {request.content_type}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Body: {request.body}")
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print(f"Parsed JSON: {json.dumps(data, indent=2)[:500]}")
        except Exception as e:
            print(f"Could not parse JSON: {e}")
    
    return JsonResponse({
        'status': 'debug_ok',
        'method': request.method,
        'path': request.path,
        'message': 'Debug endpoint working!'
    }, status=200)


# =============================================
# TEST ENDPOINTS
# =============================================

@csrf_exempt
def test_webhook(request):
    """Simple test endpoint"""
    print("=" * 50)
    print("🔍 TEST ENDPOINT CALLED!")
    print(f"🔍 Method: {request.method}")
    print(f"🔍 GET params: {dict(request.GET)}")
    print(f"🔍 Headers: {dict(request.headers)}")
    print(f"🔍 Body: {request.body}")
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print(f"🔍 Parsed JSON: {json.dumps(data, indent=2)[:500]}")
        except Exception as e:
            print(f"🔍 Could not parse JSON: {e}")
    
    return JsonResponse({
        'status': 'test_ok',
        'method': request.method,
        'path': request.path,
    }, status=200)


@csrf_exempt
def test_food_items(request):
    """Test endpoint to check food items"""
    from .models import FoodItem
    
    food_items = FoodItem.objects.filter(is_active=True)
    
    items = []
    for item in food_items:
        items.append({
            'id': item.id,
            'name': item.name,
            'price': float(item.price_per_unit),
            'unit_label': item.unit_label,
            'is_active': item.is_active
        })
    
    return JsonResponse({
        'count': len(items),
        'items': items
    }, status=200)


@csrf_exempt
def test_students(request):
    """Test endpoint to check students"""
    from .models import Student
    
    students = Student.objects.filter(is_active=True)
    
    items = []
    for item in students:
        items.append({
            'id': item.id,
            'name': item.name,
            'class_name': item.class_name,
            'school': item.school,
            'is_active': item.is_active
        })
    
    return JsonResponse({
        'count': len(items),
        'items': items
    }, status=200)


@csrf_exempt
def test_patients(request):
    """Test endpoint to check patients"""
    from .models import Patient
    
    patients = Patient.objects.filter(is_active=True)
    
    items = []
    for item in patients:
        items.append({
            'id': item.id,
            'name': item.name,
            'hospital': item.hospital,
            'goal_amount': float(item.goal_amount),
            'raised_amount': float(item.raised_amount),
            'is_active': item.is_active
        })
    
    return JsonResponse({
        'count': len(items),
        'items': items
    }, status=200)


# =============================================
# WEBHOOK - MAIN ENTRY POINT
# =============================================

@csrf_exempt
def webhook(request):
    """Handle WhatsApp webhook events"""
    from .services.views import webhook_handler
    return webhook_handler(request)


# =============================================
# INTERACTIVE WHATSAPP SERVICE FUNCTIONS
# =============================================

def send_text_message(phone_number, message):
    """Send a plain text message"""
    try:
        url = f"https://graph.facebook.com/v18.0/{settings.PHONE_NUMBER_ID}/messages"
        headers = {
            'Authorization': f'Bearer {settings.WHATSAPP_TOKEN}',
            'Content-Type': 'application/json'
        }
        data = {
            'messaging_product': 'whatsapp',
            'to': phone_number,
            'type': 'text',
            'text': {'body': message}
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"✅ Text message sent to {phone_number}")
        return response.json()
    except Exception as e:
        print(f"❌ Error sending text message: {str(e)}")
        raise


# =============================================
# INTERACTIVE MENU FUNCTIONS
# =============================================

from .whatsapp_service import whatsapp_service

def send_main_menu(phone_number):
    """Send main menu with interactive buttons"""
    body_text = """Welcome to Thaagam Foundation.

Please choose one of the following options."""
    
    buttons = [
        {'type': 'reply', 'reply': {'id': 'donate', 'title': '❤️ Donate'}},
        {'type': 'reply', 'reply': {'id': 'contact', 'title': '📞 Contact'}},
        {'type': 'reply', 'reply': {'id': 'location', 'title': '📍 Location'}},
    ]
    
    whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text='Welcome to Thaagam Foundation'
    )


def send_donation_categories(phone_number):
    """Send donation categories with interactive buttons"""
    body_text = """🙏 *Choose a Donation Cause:*

Please select a donation category."""
    
    buttons = [
        {'type': 'reply', 'reply': {'id': 'donate_food', 'title': '🍛 Food'}},
        {'type': 'reply', 'reply': {'id': 'donate_education', 'title': '🎓 Education'}},
        {'type': 'reply', 'reply': {'id': 'donate_medical', 'title': '🏥 Medical'}},
    ]
    
    whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text='❤️ Choose Donation Category'
    )


def send_contact_info(phone_number):
    """Send contact information"""
    body_text = """📞 *Contact Thaagam Foundation*

📱 Phone: +91 93456 55206
✉️ Email: foundation@thaagam.org
🌐 Website: https://thaagam.org

We'd love to hear from you!"""
    
    buttons = [
        {'type': 'reply', 'reply': {'id': 'menu', 'title': '🔙 Main Menu'}}
    ]
    
    whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text='📞 Contact Us'
    )


def send_location_info(phone_number):
    """Send location information"""
    body_text = """📍 *Thaagam Foundation – Registered Office*

🏢 Thaagam Foundation
123, Main Street,
Chennai, Tamil Nadu – 600001,
India

Visit us to learn more!"""
    
    buttons = [
        {'type': 'reply', 'reply': {'id': 'menu', 'title': '🔙 Main Menu'}}
    ]
    
    whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text='📍 Our Location'
    )


def send_review_and_payment(phone_number, donation):
    """Send review and payment option"""
    body_text = f"""📋 *Donation Review*

🔖 *Reference:* {donation.reference_number}
🎯 *Cause:* {donation.get_cause_display()}
💰 *Amount:* ₹{donation.amount:,.0f}

Please review your donation details above.

Click the button below to proceed to payment."""
    
    buttons = [
        {'type': 'reply', 'reply': {'id': 'proceed_payment', 'title': '💳 Proceed to Pay'}},
        {'type': 'reply', 'reply': {'id': 'menu', 'title': '🔙 Cancel'}}
    ]
    
    whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text='✅ Review Donation'
    )


def send_payment_link(phone_number, donation):
    """Send payment link via Easebuzz"""
    from .whatsapp_service import whatsapp_service

    try:
        body_text = f"""Your donation has been saved successfully.

Grand Total: ₹{donation.amount:,.0f}

Payment Status: Pending

Click the button below to complete your payment."""

        # Using the centralized whatsapp_service to send the message
        whatsapp_service.send_interactive_cta_url(
            to_phone_number=phone_number,
            body_text=body_text,
            button_text="Pay Now",
            url=settings.THAAGAM_PAY_NOW_URL,
            header_text="💳 Complete Your Payment"
        )
        # Reset session after sending payment link
        from .models import WhatsAppSession
        session = WhatsAppSession.objects.get(whatsapp_phone_number=phone_number)
        reset_to_menu(phone_number, session)
    except Exception as e:
        print(f"❌ Error sending CTA URL button: {str(e)}")


# =============================================
# DONATION CREATION FUNCTIONS
# =============================================

def create_donation(phone_number, session, category):
    """Create donation based on category"""
    data = session.session_data
    from .models import Donation, DonationItem, DonationPackage

    try:
        # Calculate total amount
        total_amount = data.get('total_amount', 0)
        
        # Create donation
        donation = Donation.objects.create(
            whatsapp_phone_number=phone_number,
            category=category,
            cause=category,
            amount=total_amount,
            full_name=data.get('full_name', ''),
            mobile_number=data.get('mobile_number', ''),
            email=data.get('email', ''),
            instagram_id=data.get('instagram_id', ''),
            payment_status='PENDING',
        )
        
        # Save donation items based on category
        if category == 'FOOD':
            food_item = data.get('selected_food_item', {})
            DonationItem.objects.create(
                donation=donation,
                item_type='FOOD',
                item_name=food_item.get('name', 'Food Item'),
                item_id=str(food_item.get('id', '')),
                quantity=data.get('quantity', 1),
                unit_price=food_item.get('price', 0),
                subtotal=data.get('total_amount', 0),
            )
            
            # Save packages
            for pkg in data.get('selected_packages', []):
                DonationPackage.objects.create(
                    donation=donation,
                    package_name=pkg.get('name', 'Package'),
                    price=pkg.get('price', 0),
                )
        
        elif category == 'EDUCATION':
            student = data.get('selected_student', {})
            if student:
                donation.student_id = student.get('id')
                donation.save()
                
                DonationItem.objects.create(
                    donation=donation,
                    item_type='EDUCATION',
                    item_name=f"Sponsorship - {student.get('name', 'Student')}",
                    item_id=str(student.get('id', '')),
                    quantity=1,
                    unit_price=total_amount,
                    subtotal=total_amount,
                )
        
        elif category == 'MEDICAL':
            patient = data.get('selected_patient', {})
            if patient:
                donation.patient_id = patient.get('id')
                donation.save()
                
                DonationItem.objects.create(
                    donation=donation,
                    item_type='MEDICAL',
                    item_name=f"Medical Support - {patient.get('name', 'Patient')}",
                    item_id=str(patient.get('id', '')),
                    quantity=1,
                    unit_price=total_amount,
                    subtotal=total_amount,
                )
        
        # --- CONSOLIDATED DONOR DETAILS & PAYMENT LINK ---
        # 1. Build the single, formatted donor details message.
        confirmation_message = f"""📝 *Donor Details*

👤 *Name:*
{donation.full_name}

📧 *Email Address:*
{donation.email}

📱 *Mobile Number:*
{donation.mobile_number}

📸 *Instagram ID:*
{donation.instagram_id or 'Not Provided'}

💰 *Donation Amount:*
₹{donation.amount:,.0f}

✅ *Payment Status:* Pending

Please review your details carefully.

Click the button below to complete your payment."""

        # 2. Send the message with the "Pay Now" CTA button.
        whatsapp_service.send_interactive_cta_url(
            to_phone_number=phone_number,
            body_text=confirmation_message,
            button_text="💳 Pay Now",
            url=settings.THAAGAM_PAY_NOW_URL,
            header_text="✅ Confirm Your Donation"
        )

        reset_to_menu(phone_number, session)
        session.save()
        print(f"✅ Donation created: {donation.reference_number}")
        
    except Exception as e:
        print(f"❌ Error creating donation: {str(e)}")
        import traceback
        traceback.print_exc()
        send_text_message(phone_number, "❌ Error creating donation. Please try again.")
        # Reset to menu on failure
        reset_to_menu(phone_number, session)

def send_payment_link(phone_number, donation):
    """Send payment link via Easebuzz"""
    from .whatsapp_service import whatsapp_service

    try:
        body_text = f"""Your donation has been saved successfully.

Grand Total: ₹{donation.amount:,.0f}

Payment Status: Pending

Click the button below to complete your payment."""

        # Using the centralized whatsapp_service to send the message
        whatsapp_service.send_interactive_cta_url(
            to_phone_number=phone_number,
            body_text=body_text,
            button_text="Pay Now",
            url=settings.THAAGAM_PAY_NOW_URL,
            header_text="💳 Complete Your Payment"
        )
        # Reset session after sending payment link
        from .models import WhatsAppSession
        session = WhatsAppSession.objects.get(whatsapp_phone_number=phone_number)
        reset_to_menu(phone_number, session)
    except Exception as e:
        print(f"❌ Error sending CTA URL button: {str(e)}")

def handle_proceed_payment(phone_number, session):
    """Handle proceed to payment button click"""
    data = session.session_data
    donation_id = data.get('donation_id')
    
    if not donation_id:
        send_text_message(phone_number, "❌ No donation found. Please start over.")
        reset_to_menu(phone_number, session)
        return
    
    from .models import Donation
    try:
        donation = Donation.objects.get(id=donation_id)
        send_payment_link(phone_number, donation)
        
        # Reset session after payment link sent
        session.current_state = 'MENU'
        session.session_data = {}
        session.save()
        
    except Donation.DoesNotExist:
        send_text_message(phone_number, "❌ Donation not found. Please start over.")
        reset_to_menu(phone_number, session)


def reset_to_menu(phone_number, session):
    """Reset session to main menu"""
    session.current_state = 'MENU'
    session.session_data = {}
    session.save()
    send_main_menu(phone_number)


# =============================================
# FOOD DONATION FLOW
# =============================================

def send_food_items_interactive(phone_number, food_items):
    """Send food items as an interactive list"""
    try:
        if not food_items.exists():
            send_text_message(phone_number, "🍽️ No food items available at this time.")
            return False
        
        rows = []
        for item in food_items:
            rows.append({
                'id': f'food_item_{item.id}',
                'title': item.name[:24],
                'description': f"₹{item.price_per_unit}/{item.unit_label}"[:72]
            })
        
        sections = [{'title': '🍽️ Available Food Items', 'rows': rows}]
        
        return whatsapp_service.send_interactive_list(
            phone_number,
            "Please select a food item you'd like to donate:",
            "Select Food Item",
            sections,
            header_text='🍽️ Food Donation',
            footer_text='❤️ Thaagam Foundation'
        )
    except Exception as e:
        print(f"❌ Error in send_food_items_interactive: {str(e)}")
        return False


def send_food_quantity_selection(phone_number, food_item):
    """Send quantity selection for food item"""
    body_text = f"""🍽️ *Selected Food Item*

You selected: *{food_item['name']}*
Price: ₹{food_item['price']}/{food_item['unit_label']}

Please enter the quantity you want to donate."""
    
    buttons = [
        {'type': 'reply', 'reply': {'id': 'qty_1', 'title': '1'}},
        {'type': 'reply', 'reply': {'id': 'qty_2', 'title': '2'}},
        {'type': 'reply', 'reply': {'id': 'qty_5', 'title': '5'}}
    ]
    
    whatsapp_service.send_interactive_buttons(
        phone_number,
        body_text,
        buttons,
        header_text='📦 Select Quantity'
    )


def send_packages_selection(phone_number, session):
    """Send packages selection for food donation"""
    from .models import Package
    
    packages = Package.objects.filter(is_active=True, category__in=['FOOD', 'ALL'])
    
    if not packages.exists():
        session.current_state = 'FOOD_DONOR_INFO'
        session.save()
        send_donor_info_form(phone_number)
        return
    
    rows = []
    for pkg in packages:
        rows.append({
            'id': str(pkg.id),
            'title': pkg.name[:24],
            'description': f"₹{pkg.price}"[:72]
        })
    
    rows.append({
        'id': 'skip_packages',
        'title': 'Skip Packages',
        'description': 'Continue without packages'
    })
    
    sections = [{'title': '🎁 Optional Packages', 'rows': rows}]
    
    whatsapp_service.send_interactive_list(
        phone_number,
        "Select packages to add to your donation (optional):",
        "Select Package",
        sections,
        header_text='🎁 Donation Packages',
        footer_text='❤️ Thaagam Foundation'
    )


# =============================================
# EDUCATION DONATION FLOW
# =============================================

def send_student_list_interactive(phone_number, students):
    """Send student list as interactive list"""
    try:
        if not students.exists():
            send_text_message(phone_number, "📚 No students available at this time.")
            return False
        
        rows = []
        for student in students:
            rows.append({
                'id': f'student_{student.id}',
                'title': student.name[:24],
                'description': f"{student.class_name}, {student.school}"[:72]
            })
        
        sections = [{'title': '📚 Students List', 'rows': rows}]
        
        return whatsapp_service.send_interactive_list(
            phone_number,
            "Please select a student you'd like to sponsor:",
            "Select Student",
            sections,
            header_text='📚 Education Sponsorship',
            footer_text='❤️ Thaagam Foundation'
        )
    except Exception as e:
        print(f"❌ Error in send_student_list_interactive: {str(e)}")
        return False


def send_education_amount_selection(phone_number, student_name):
    """Send amount selection for education donation"""
    body_text = f"""📚 *Sponsor Student: {student_name}*

Please enter your donation amount (minimum ₹100)."""
    send_text_message(phone_number, body_text)


# =============================================
# MEDICAL DONATION FLOW
# =============================================

def send_patient_list_interactive(phone_number, patients):
    """Send patient list as interactive list"""
    try:
        if not patients.exists():
            send_text_message(phone_number, "🏥 No patients available at this time.")
            return False
        
        rows = []
        for patient in patients:
            remaining = patient.goal_amount - patient.raised_amount
            rows.append({
                'id': f'patient_{patient.id}',
                'title': patient.name[:24],
                'description': f"₹{remaining:,.0f} needed"[:72]
            })
        
        sections = [{'title': '🏥 Patients List', 'rows': rows}]
        
        return whatsapp_service.send_interactive_list(
            phone_number,
            "Please select a patient you'd like to support:",
            "Select Patient",
            sections,
            header_text='🏥 Medical Assistance',
            footer_text='❤️ Thaagam Foundation'
        )
    except Exception as e:
        print(f"❌ Error in send_patient_list_interactive: {str(e)}")
        return False


def send_medical_amount_selection(phone_number, patient_name):
    """Send amount selection for medical donation"""
    body_text = f"""🏥 *Support Patient: {patient_name}*

Please enter your donation amount (minimum ₹100)."""
    send_text_message(phone_number, body_text)


# =============================================
# CHATBOT STATE HANDLER
# =============================================

def handle_chatbot_state(phone_number, session, msg_text, msg_text_raw):
    """Handle state-based conversations"""
    from .services.validation_service import parse_donor_details, validate_donor_details, send_validation_errors, validate_quantity, validate_amount
    state = session.current_state
    data = session.session_data or {}
    
    # ====== FOOD FLOW ======
    if state == 'FOOD_ITEM_SELECT':
        try:
            if not msg_text.startswith('food_item_'):
                raise ValueError("Invalid food item ID format")
            
            from .models import FoodItem
            item_id = int(msg_text.replace('food_item_', ''))
            item = FoodItem.objects.get(id=item_id, is_active=True)
            
            data['selected_food_item'] = {
                'id': item.id,
                'name': item.name,
                'price': float(item.price_per_unit),
                'unit_label': item.unit_label
            }
            session.session_data = data
            session.current_state = 'FOOD_QTY'
            session.save()
            
            send_food_quantity_selection(phone_number, data['selected_food_item'])
            
        except (ValueError, FoodItem.DoesNotExist) as e:
            print(f"❌ Error selecting food item: {str(e)}")
            send_text_message(phone_number, "❌ Invalid selection. Please try again.")
            from .models import FoodItem
            food_items = FoodItem.objects.filter(is_active=True)
            send_food_items_interactive(phone_number, food_items)
    
    elif state == 'FOOD_QTY':
        try:
            if msg_text.startswith('qty_'):
                qty_str = msg_text.split('_')[1]
            else:
                qty_str = msg_text_raw.strip()

            qty, errors = validate_quantity(qty_str)
            if errors:
                send_validation_errors(phone_number, errors)
                return

            item = data['selected_food_item']
            total = qty * item['price']
            
            data['quantity'] = qty
            data['total_amount'] = total
            session.session_data = data
            session.current_state = 'FOOD_PACKAGES'
            session.save()
            
            send_packages_selection(phone_number, session)

        except (ValueError, TypeError):
            send_text_message(phone_number, "❌ Please enter a valid quantity (e.g., 5).")
    
    elif state == 'FOOD_PACKAGES':
        from .models import Package
        data = session.session_data

        # Handle both skipping and selecting a package
        try:
            selected_packages = data.get('selected_packages', [])
            package_total = data.get('package_total', 0)
            food_total = data.get('total_amount', 0)

            if msg_text != 'skip_packages':
                pkg_id = int(msg_text)
                package = Package.objects.get(id=pkg_id, is_active=True)
                
                # Avoid adding duplicates
                if not any(p['id'] == package.id for p in selected_packages):
                    selected_packages.append({
                        'id': package.id,
                        'name': package.name,
                        'price': float(package.price)
                    })
                    package_total += float(package.price)

            # Update session data
            data['selected_packages'] = selected_packages
            data['package_total'] = package_total
            # Recalculate grand total
            base_food_total = food_total - (package_total - (float(package.price) if msg_text != 'skip_packages' else 0))
            data['total_amount'] = base_food_total + package_total
            
            session.session_data = data
            session.current_state = 'FOOD_DONOR_INFO'
            session.save()
            
            handle_chatbot_state(phone_number, session, msg_text, msg_text_raw) # Trigger first step of form

        except (ValueError, Package.DoesNotExist):
            data['selected_packages'] = []
            data['package_total'] = 0
            session.session_data = data
            session.current_state = 'FOOD_DONOR_INFO'
            session.save()
            handle_chatbot_state(phone_number, session, msg_text, msg_text_raw) # Trigger first step of form
    
    elif state == 'FOOD_REVIEW':
        if msg_text == 'proceed_payment':
            create_donation(phone_number, session, 'FOOD')
        else:
            send_text_message(phone_number, "Please click 'Proceed to Pay' to complete your donation.")
    
    # ====== EDUCATION FLOW ======
    elif state == 'EDU_STUDENT_SELECT':
        try:
            if not msg_text.startswith('student_'):
                raise ValueError("Invalid student ID format")
            
            student_id = int(msg_text.replace('student_', ''))
            from .models import Student
            student = Student.objects.get(id=student_id, is_active=True)
            
            data['selected_student'] = {
                'id': student.id,
                'name': student.name,
                'class_name': student.class_name,
                'school': student.school
            }
            session.session_data = data
            session.current_state = 'EDU_AMOUNT'
            session.save()
            
            send_education_amount_selection(phone_number, student.name)
            
        except (ValueError, Student.DoesNotExist) as e:
            print(f"❌ Error selecting student: {str(e)}")
            send_text_message(phone_number, "❌ Invalid selection. Please try again.")
            from .models import Student
            students = Student.objects.filter(is_active=True)
            send_student_list_interactive(phone_number, students)
    
    elif state == 'EDU_AMOUNT':
        try:
            amount = float(msg_text_raw.strip())
            if amount < 100:
                send_text_message(phone_number, "❌ Minimum donation is ₹100. Please enter a higher amount:")
                return
            
            data['donation_amount'] = amount
            data['total_amount'] = amount
            session.session_data = data
            session.current_state = 'EDU_DONOR_INFO'
            session.save()
            
            handle_chatbot_state(phone_number, session, msg_text, msg_text_raw) # Trigger first step of form
            
        except ValueError:
            send_text_message(phone_number, "❌ Please enter a valid amount:")
    
    elif state == 'EDUCATION_REVIEW':
        if msg_text == 'proceed_payment':
            create_donation(phone_number, session, 'EDUCATION')
        else:
            send_text_message(phone_number, "Please click 'Proceed to Pay' to complete your donation.")
    
    # ====== MEDICAL FLOW ======
    elif state == 'MED_PATIENT_SELECT':
        try:
            if not msg_text.startswith('patient_'):
                raise ValueError("Invalid patient ID format")
            
            patient_id = int(msg_text.replace('patient_', ''))
            from .models import Patient
            patient = Patient.objects.get(id=patient_id, is_active=True)
            
            data['selected_patient'] = {
                'id': patient.id,
                'name': patient.name,
                'hospital': patient.hospital,
                'goal_amount': float(patient.goal_amount),
                'raised_amount': float(patient.raised_amount)
            }
            session.session_data = data
            session.current_state = 'MED_AMOUNT'
            session.save()
            
            send_medical_amount_selection(phone_number, patient.name)
            
        except (ValueError, Patient.DoesNotExist) as e:
            print(f"❌ Error selecting patient: {str(e)}")
            send_text_message(phone_number, "❌ Invalid selection. Please try again.")
            from .models import Patient
            patients = Patient.objects.filter(is_active=True)
            send_patient_list_interactive(phone_number, patients)
    
    elif state == 'MED_AMOUNT':
        try:
            amount = float(msg_text_raw.strip())
            if amount < 100:
                send_text_message(phone_number, "❌ Minimum donation is ₹100. Please enter a higher amount:")
                return
            
            data['donation_amount'] = amount
            data['total_amount'] = amount
            session.session_data = data
            session.current_state = 'MED_DONOR_INFO'
            session.save()
            
            handle_chatbot_state(phone_number, session, msg_text, msg_text_raw) # Trigger first step of form
            
        except ValueError:
            send_text_message(phone_number, "❌ Please enter a valid amount:")
    
    elif state == 'MEDICAL_REVIEW':
        if msg_text == 'proceed_payment':
            create_donation(phone_number, session, 'MEDICAL')
        else:
            send_text_message(phone_number, "Please click 'Proceed to Pay' to complete your donation.")
    
    else:
        send_text_message(phone_number, "❌ I didn't understand that. Please type 'Hi' to restart.")


# =============================================
# EASEBUZZ CALLBACK
# =============================================

@csrf_exempt
@require_http_methods(["POST"])
def easebuzz_callback(request):
    """Webhook callback from Easebuzz payment gateway"""
    try:
        data = request.POST.dict()
        print(f"Easebuzz callback received: {json.dumps(data, indent=2)}")
        
        txnid = data.get('txnid')
        status = data.get('status')
        reference_number = data.get('udf1', '')
        
        if not reference_number:
            return HttpResponse("Missing reference number", status=400)
        
        from .models import Donation
        try:
            donation = Donation.objects.get(reference_number=reference_number)
        except Donation.DoesNotExist:
            print(f"Donation with reference {reference_number} not found")
            return HttpResponse("Donation not found", status=404)
        
        if status == 'success':
            donation.payment_status = 'COMPLETED'
            donation.payment_id = txnid
            donation.payment_response = data
            donation.save()
            
            body_text = f"""🎉 *Payment Successful!*

Thank you for your generous donation!

🔖 *Reference:* {donation.reference_number}
🎯 *Cause:* {donation.get_cause_display()}
💰 *Amount:* ₹{donation.amount:,.0f}

Your support makes a difference! ❤️"""
            
            buttons = [
                {'type': 'reply', 'reply': {'id': 'menu', 'title': '🏠 Main Menu'}},
                {'type': 'reply', 'reply': {'id': 'donate', 'title': '💝 Donate Again'}}
            ]
            
            whatsapp_service.send_interactive_buttons(
                donation.whatsapp_phone_number,
                body_text,
                buttons,
                header_text='✅ Payment Successful'
            )
            
        elif status == 'failure':
            donation.payment_status = 'FAILED'
            donation.payment_response = data
            donation.save()
            
            body_text = f"""❌ *Payment Failed*

Your payment for donation {donation.reference_number} has failed.

Please try again or contact us for support."""
            
            buttons = [
                {'type': 'reply', 'reply': {'id': 'donate', 'title': '💝 Try Again'}},
                {'type': 'reply', 'reply': {'id': 'menu', 'title': '🏠 Main Menu'}}
            ]
            
            whatsapp_service.send_interactive_buttons(
                donation.whatsapp_phone_number,
                body_text,
                buttons,
                header_text='❌ Payment Failed'
            )
        
        return HttpResponse("Callback processed successfully")
        
    except Exception as e:
        print(f"Error in easebuzz callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse("Error", status=500)


# =============================================
# UPLOAD LOGO
# =============================================

@csrf_exempt
def upload_logo(request):
    """Upload Thaagam Foundation logo to WhatsApp"""
    image_path = os.path.join(settings.MEDIA_ROOT, 'whatsapp_images', 'thaagam_logo.png')
    
    if not os.path.exists(image_path):
        return JsonResponse({
            'success': False,
            'error': f'Image not found at: {image_path}',
        }, status=404)
    
    access_token = settings.WHATSAPP_TOKEN
    phone_number_id = settings.PHONE_NUMBER_ID
    
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': ('thaagam_logo.png', f, 'image/png')}
            data = {'messaging_product': 'whatsapp'}
            
            response = requests.post(url, headers=headers, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            media_id = result.get('id')
            
            return JsonResponse({
                'success': True,
                'media_id': media_id,
                'message': 'Image uploaded successfully!',
                'next_step': f'Add this to settings.py: HEADER_IMAGE_ID = "{media_id}"'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


# =============================================
# FLOW ENDPOINT
# =============================================

@csrf_exempt
def flow_endpoint(request):
    """Handle WhatsApp Flow encrypted data"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"Flow endpoint data received")
            
            if 'flow_id' in data:
                flow_id = data.get('flow_id')
                payload = data.get('payload', {})
                
                action = payload.get('action')
                if action == 'submit':
                    form_data = payload.get('data', {})
                    print(f"Flow form submitted")
                    
                    phone_number = form_data.get('donor_whatsapp')
                    if phone_number:
                        process_flow_submission(phone_number, form_data, flow_id)
                
                return JsonResponse({'status': 'success'})
            
            return JsonResponse({'status': 'ignored'}, status=200)
            
        except Exception as e:
            print(f"Flow endpoint error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=200)
    
    return JsonResponse({'status': 'ok'})


def process_flow_submission(phone_number, form_data, flow_id):
    """Process flow form submission"""
    try:
        from .models import Donation
        
        name = form_data.get('donor_name', '')
        email = form_data.get('donor_email', '')
        amount = form_data.get('amount', 0)
        cause = 'FOOD' if flow_id == settings.FOOD_FLOW_ID else 'EDUCATION'
        
        donation = Donation.objects.create(
            whatsapp_phone_number=phone_number,
            category=cause,
            cause=cause,
            amount=float(amount),
            full_name=name,
            email=email,
            mobile_number=phone_number,
            payment_status='PENDING',
        )
        
        send_review_and_payment(phone_number, donation)
        
    except Exception as e:
        print(f"Error processing flow submission: {str(e)}")
        import traceback
        traceback.print_exc()