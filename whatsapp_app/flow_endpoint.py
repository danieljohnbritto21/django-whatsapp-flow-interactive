"""
WhatsApp Flow Data Endpoint

Handles dynamic data exchange between WhatsApp Flows and the Django backend.
This is the encrypted endpoint that WhatsApp calls when a Flow needs data
or when a user navigates between screens.

Actions handled:
    - ping: Health check
    - INIT: Initial screen data load
    - data_exchange: Screen-to-screen navigation with dynamic data
    - complete: Flow submission — saves donation and triggers payment
"""

import json
import logging
import urllib.parse
from decimal import Decimal

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    FoodItem, Student, Patient, Package,
    Donation, DonationItem, DonationPackage,
)
from .easebuzz_service import easebuzz_service

logger = logging.getLogger(__name__)


# ==================== SIMPLE ENCRYPTION FALLBACK ====================

class SimpleFlowEncryption:
    """
    Simple encryption fallback when cryptography is not available.
    This is a placeholder - in production, use proper encryption.
    """
    
    def __init__(self):
        self.is_configured = False
    
    def decrypt_request(self, encrypted_data, encrypted_key, iv):
        """Simple passthrough for testing"""
        try:
            # Try to decode as JSON
            import base64
            decoded = base64.b64decode(encrypted_data).decode('utf-8')
            return json.loads(decoded), None, None
        except:
            return {}, None, None
    
    def encrypt_response(self, response_data, aes_key, iv):
        """Simple passthrough for testing"""
        import base64
        return base64.b64encode(json.dumps(response_data).encode('utf-8')).decode('utf-8')


# Try to import real encryption, fallback to simple
try:
    from .flow_encryption import flow_encryption
except ImportError:
    logger.warning("flow_encryption not found, using simple fallback")
    flow_encryption = SimpleFlowEncryption()


# ==================== COMMON HELPERS ====================

def _common_screen_data():
    """Return common data fields included in every screen response."""
    return {
        'header_image': getattr(settings, 'THAAGAM_LOGO_URL', ''),
    }


def get_payment_redirect_url(donation, easebuzz_payment_url=None):
    """
    Generate the redirect URL to the Thaagam Foundation website
    with all donation details as query parameters.
    """
    base_url = 'https://www.thaagam.org/causes-detail/thaali/'
    
    # Query items
    donation_items = DonationItem.objects.filter(donation=donation)
    items_list = []
    food_total = Decimal('0')
    for item in donation_items:
        items_list.append({
            'name': item.item_name,
            'qty': item.quantity,
            'price': str(item.unit_price),
            'subtotal': str(item.subtotal)
        })
        food_total += item.subtotal

    # Query packages
    donation_packages = DonationPackage.objects.filter(donation=donation)
    packages_list = []
    pkg_total = Decimal('0')
    for pkg in donation_packages:
        packages_list.append({
            'name': pkg.package_name,
            'price': str(pkg.price)
        })
        pkg_total += pkg.price

    # Form parameters
    params = {
        'category': donation.category or 'FOOD',
        'food_items': json.dumps(items_list),
        'food_total': str(food_total),
        'selected_packages': json.dumps(packages_list),
        'package_total': str(pkg_total),
        'grand_total': str(donation.amount),
        'donor_name': donation.full_name,
        'email': donation.email,
        'phone': donation.mobile_number,
        'instagram': donation.instagram_id or '',
        'reference_number': donation.reference_number,
    }
    if easebuzz_payment_url:
        params['easebuzz_payment_url'] = easebuzz_payment_url
        
    return f"{base_url}?{urllib.parse.urlencode(params)}"


# ==================== MAIN ENDPOINT ====================

@csrf_exempt
@require_http_methods(["POST"])
def flow_data_endpoint(request):
    """
    Encrypted data endpoint for WhatsApp Native Flows.

    WhatsApp sends encrypted payloads containing:
        - encrypted_flow_data: AES-GCM encrypted request body
        - encrypted_aes_key: RSA-encrypted AES key
        - initial_vector: AES-GCM IV

    We decrypt, process, encrypt the response, and return it as text/plain.
    """
    try:
        body = json.loads(request.body)

        # Handle health check (ping)
        if body.get('action') == 'ping':
            logger.info("Flow endpoint health check — ping received")
            return JsonResponse({'data': {'status': 'active'}})

        # Check if we have encrypted data
        if 'encrypted_flow_data' in body:
            # Decrypt the request
            if not flow_encryption.is_configured:
                logger.warning("Flow encryption not configured, using raw data")
                decrypted_data = body.get('data', {})
            else:
                decrypted_data, aes_key, iv = flow_encryption.decrypt_request(
                    body['encrypted_flow_data'],
                    body['encrypted_aes_key'],
                    body['initial_vector']
                )
        else:
            # No encryption, use raw data
            decrypted_data = body.get('data', {})

        logger.info(f"Flow request — action: {decrypted_data.get('action')}, "
                     f"screen: {decrypted_data.get('screen')}")

        # Route to the appropriate handler
        action = decrypted_data.get('action', '')
        screen = decrypted_data.get('screen', '')
        data = decrypted_data.get('data', {})
        flow_token = decrypted_data.get('flow_token', '')

        if action == 'INIT':
            response_data = handle_init(screen, data, flow_token)
        elif action == 'data_exchange':
            response_data = handle_data_exchange(screen, data, flow_token)
        elif action == 'complete':
            response_data = handle_complete(screen, data, flow_token)
        else:
            # Default response
            response_data = {
                'screen': screen or 'cause_selection',
                'data': {}
            }

        # Encrypt and return response
        if 'encrypted_flow_data' in body and flow_encryption.is_configured:
            encrypted_response = flow_encryption.encrypt_response(response_data, aes_key, iv)
            return HttpResponse(encrypted_response, content_type='text/plain')
        else:
            return JsonResponse(response_data)

    except KeyError as e:
        logger.error(f"Flow endpoint missing field: {str(e)}")
        return JsonResponse({'error': f'Missing field: {str(e)}'}, status=400)
    except Exception as e:
        logger.error(f"Flow endpoint error: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ==================== INIT HANDLER ====================

def handle_init(screen, data, flow_token):
    """Handle INIT action — return initial data for the first screen."""
    logger.info(f"INIT action: screen={screen}, flow_token={flow_token}")
    
    # --- FOOD FORM HANDLER ---
    if screen == 'food_donation_form':
        return handle_food_form_screen(screen, data, flow_token)
    
    flow_type = data.get('flow_type', '')
    if not flow_type and flow_token:
        if 'food' in flow_token.lower():
            flow_type = 'FOOD'
        elif 'education' in flow_token.lower():
            flow_type = 'EDUCATION'
        elif 'medical' in flow_token.lower():
            flow_type = 'MEDICAL'
            
    logger.info(f"Resolved flow_type={flow_type}")

    if flow_type == 'FOOD':
        return get_food_list_data()
    elif flow_type == 'EDUCATION':
        return get_student_list_data()
    elif flow_type == 'MEDICAL':
        return get_patient_list_data()
    else:
        # Fallback based on screen name
        if screen == 'STUDENT_LIST':
            return get_student_list_data()
        elif screen == 'PATIENT_LIST':
            return get_patient_list_data()
        return get_food_list_data()


# ==================== DATA EXCHANGE HANDLER ====================

def handle_data_exchange(screen, data, flow_token):
    """Handle data_exchange action — process current screen and return next screen data."""

    logger.info(f"Data exchange — screen: {screen}, data keys: {list(data.keys())}")

    # --- FOOD FORM HANDLER ---
    if screen == 'food_donation_form':
        return handle_food_form_complete(data, flow_token)
    elif screen == 'FOOD_REVIEW':
        # This is a terminal screen, but if data_exchange is called,
        # it's likely a back button press. We can just re-evaluate.
        return handle_food_packages_submit(data)

    # --- FOOD FLOW ---
    if screen == 'FOOD_LIST':
        return handle_food_list_submit(data)
    elif screen == 'FOOD_DONOR_INFO':
        return handle_food_donor_info_submit(data)
    elif screen == 'FOOD_PACKAGES':
        return handle_food_packages_submit(data)

    # --- EDUCATION FLOW ---
    elif screen == 'STUDENT_LIST':
        return handle_student_select(data)
    elif screen == 'EDU_DONATION_AMOUNT':
        return handle_edu_amount_submit(data)
    elif screen == 'EDU_DONOR_INFO':
        return handle_edu_donor_info_submit(data)

    # --- MEDICAL FLOW ---
    elif screen == 'PATIENT_LIST':
        return handle_patient_select(data)
    elif screen == 'MED_DONATION_AMOUNT':
        return handle_med_amount_submit(data)
    elif screen == 'MED_DONOR_INFO':
        return handle_med_donor_info_submit(data)

    else:
        return {
            'screen': 'ERROR',
            'data': {'error_message': f'Unknown screen: {screen}'}
        }


# ==================== COMPLETE HANDLER ====================

def handle_complete(screen, data, flow_token):
    """Handle complete action — save donation and prepare for payment."""

    logger.info(f"Flow complete — screen: {screen}")

    try:
        flow_type = data.get('flow_type', 'FOOD')

        if flow_type == 'FOOD':
            donation = save_food_donation(data)
        elif flow_type == 'EDUCATION':
            donation = save_education_donation(data)
        elif flow_type == 'MEDICAL':
            donation = save_medical_donation(data)
        else:
            return {
                'screen': 'ERROR',
                'data': {'error_message': f'Unknown flow type: {flow_type}'}
            }

        redirect_url = get_payment_redirect_url(donation)
        return {
            'screen': 'SUCCESS',
            'data': {
                **_common_screen_data(),
                'extension_message_response': {
                    'params': {
                        'flow_token': flow_token,
                        'reference_number': donation.reference_number,
                        'amount': str(donation.amount),
                        'payment_url': redirect_url,
                        'status': 'PAYMENT_INITIATED',
                    }
                }
            }
        }

    except Exception as e:
        logger.error(f"Error completing flow: {str(e)}", exc_info=True)
        return {
            'screen': 'SUCCESS',
            'data': {
                **_common_screen_data(),
                'extension_message_response': {
                    'params': {
                        'flow_token': flow_token,
                        'status': 'ERROR',
                        'error': str(e),
                    }
                }
            }
        }


# ==================== FOOD FLOW HANDLERS ====================

def get_food_list_data():
    """Get food items for the FOOD_LIST screen."""
    food_items = FoodItem.objects.filter(is_active=True)

    # Build quantity options (0-10)
    qty_options = [{'id': str(i), 'title': str(i)} for i in range(11)]

    items_data = []
    for item in food_items:
        items_data.append({
            'id': str(item.id),
            'name': item.name,
            'price': str(item.price_per_unit),
            'unit': item.unit_label,
            'label': f"{item.name} — ₹{item.price_per_unit}/{item.unit_label}",
        })

    return {
        'screen': 'FOOD_LIST',
        'data': {
            **_common_screen_data(),
            'food_items': items_data,
            'qty_options': qty_options,
        }
    }


def handle_food_list_submit(data):
    """Process food selections and move to donor info screen."""
    selected_items = []
    total = Decimal('0')

    # The DynamicForm sends an array of objects.
    # Each object contains the original item data and the user's input.
    submitted_items = data.get('food_form', [])
    for submitted_item in submitted_items:
        if 'food_qty' in submitted_item and submitted_item['food_qty'] and int(submitted_item['food_qty']) > 0:
            item_id = submitted_item.get('id')
            qty = int(submitted_item['food_qty'])
            try:
                food_item = FoodItem.objects.get(id=item_id, is_active=True)
                subtotal = food_item.price_per_unit * qty
                total += subtotal
                selected_items.append({
                    'id': str(food_item.id),
                    'name': food_item.name,
                    'price': str(food_item.price_per_unit),
                    'qty': qty,
                    'subtotal': str(subtotal),
                })
            except FoodItem.DoesNotExist:
                continue

    if not selected_items:
        return {
            'screen': 'FOOD_LIST',
            'data': {
                **_common_screen_data(),
                **get_food_list_data()['data'],
                'error_message': 'Please select at least one food item.',
            }
        }

    return {
        'screen': 'FOOD_DONOR_INFO',
        'data': {
            **_common_screen_data(),
            'selected_items': json.dumps(selected_items),
            'food_total': str(total),
            'summary_text': '\n'.join([
                f"• {item['name']} × {item['qty']} = ₹{item['subtotal']}"
                for item in selected_items
            ]) + f"\n\n💰 Subtotal: ₹{total}",
            'package_interest_options': [
                {'id': 'yes', 'title': 'Yes, Show Packages'},
                {'id': 'skip', 'title': 'No, Skip'},
            ],
        }
    }


def handle_food_donor_info_submit(data):
    """Process donor info and route to packages or review based on user choice."""
    package_interest = data.get('package_interest', 'skip')
    food_total = data.get('food_total', '0')
    selected_items_json = data.get('selected_items', '[]')

    # Common donor data carried forward
    donor_data = {
        'donor_name': data.get('donor_name', ''),
        'donor_email': data.get('donor_email', ''),
        'donor_whatsapp': data.get('donor_whatsapp', ''),
        'donor_instagram': data.get('donor_instagram', ''),
        'selected_items': selected_items_json,
        'food_total': food_total,
    }

    # User chose "Yes, Show Packages"
    if package_interest == 'yes':
        packages = Package.objects.filter(
            is_active=True,
            category__in=['FOOD', 'ALL']
        )
        pkg_options = [
            {
                'id': str(pkg.id),
                'title': f"{pkg.name} — ₹{pkg.price}",
            }
            for pkg in packages
        ]

        if pkg_options:
            return {
                'screen': 'FOOD_PACKAGES',
                'data': {
                    **_common_screen_data(),
                    **donor_data,
                    'package_options': pkg_options,
                    'has_packages': True,
                }
            }
        # No packages in DB — fall through to skip

    # User chose "Skip" or no packages available — go directly to review
    selected_items = json.loads(selected_items_json)

    review_lines = ["🍲 *Selected Food Items:*"]
    for item in selected_items:
        review_lines.append(f"  • {item['name']} × {item['qty']} = ₹{item['subtotal']}")
    review_lines.append(f"\n💰 Food Total: ₹{food_total}")
    review_lines.append(f"\n📦 Packages: None (Skipped)")
    review_lines.append(f"\n🎯 *Grand Total: ₹{food_total}*")

    return {
        'screen': 'FOOD_REVIEW',
        'data': {
            **_common_screen_data(),
            **donor_data,
            'selected_packages': '[]',
            'food_total': food_total,
            'pkg_total': '0',
            'grand_total': food_total,
            'review_text': '\n'.join(review_lines),
            'flow_type': 'FOOD',
        }
    }


def handle_food_packages_submit(data):
    """Process package selection and show review screen."""
    selected_items = json.loads(data.get('selected_items', '[]'))
    food_total = Decimal(data.get('food_total', '0'))

    # Parse selected packages
    selected_pkg_ids = data.get('selected_packages', [])
    if isinstance(selected_pkg_ids, str):
        try:
            selected_pkg_ids = json.loads(selected_pkg_ids)
        except (json.JSONDecodeError, TypeError):
            selected_pkg_ids = []

    pkg_total = Decimal('0')
    selected_packages = []
    for pkg_id in selected_pkg_ids:
        try:
            pkg = Package.objects.get(id=pkg_id, is_active=True)
            pkg_total += pkg.price
            selected_packages.append({
                'id': str(pkg.id),
                'name': pkg.name,
                'price': str(pkg.price),
            })
        except Package.DoesNotExist:
            continue

    grand_total = food_total + pkg_total

    # Build review text
    review_lines = ["🍲 *Selected Food Items:*"]
    for item in selected_items:
        review_lines.append(f"  • {item['name']} × {item['qty']} = ₹{item['subtotal']}")
    review_lines.append(f"\n💰 Food Subtotal: ₹{food_total}")

    if selected_packages:
        review_lines.append("\n📦 *Selected Packages:*")
        for pkg in selected_packages:
            review_lines.append(f"  • {pkg['name']} — ₹{pkg['price']}")
        review_lines.append(f"\n📦 Package Subtotal: ₹{pkg_total}")

    review_lines.append(f"\n🎯 *Grand Total: ₹{grand_total}*")

    return {
        'screen': 'FOOD_REVIEW',
        'data': {
            **_common_screen_data(),
            'donor_name': data.get('donor_name', ''),
            'donor_email': data.get('donor_email', ''),
            'donor_whatsapp': data.get('donor_whatsapp', ''),
            'donor_instagram': data.get('donor_instagram', ''),
            'selected_items': data.get('selected_items', '[]'),
            'selected_packages': json.dumps(selected_packages),
            'food_total': str(food_total),
            'pkg_total': str(pkg_total),
            'grand_total': str(grand_total),
            'review_text': '\n'.join(review_lines),
            'flow_type': 'FOOD',
        }
    }


def save_food_donation(data):
    """Save a food donation and its items."""
    donation = Donation.objects.create(
        whatsapp_phone_number=data.get('donor_whatsapp', ''),
        category='FOOD',
        cause='FOOD',
        amount=Decimal(data.get('grand_total', '0')),
        full_name=data.get('donor_name', ''),
        mobile_number=data.get('donor_whatsapp', ''),
        email=data.get('donor_email', ''),
        instagram_id=data.get('donor_instagram', ''),
        payment_status='PENDING',
    )

    # Save food items
    selected_items = json.loads(data.get('selected_items', '[]'))
    for item in selected_items:
        DonationItem.objects.create(
            donation=donation,
            item_type='FOOD',
            item_name=item['name'],
            item_id=int(item['id']),
            quantity=int(item['qty']),
            unit_price=Decimal(item['price']),
            subtotal=Decimal(item['subtotal']),
        )

    # Save packages
    selected_packages = json.loads(data.get('selected_packages', '[]'))
    for pkg_data in selected_packages:
        try:
            pkg = Package.objects.get(id=pkg_data['id'])
            DonationPackage.objects.create(
                donation=donation,
                package=pkg,
                package_name=pkg.name,
                price=pkg.price,
            )
        except Package.DoesNotExist:
            DonationPackage.objects.create(
                donation=donation,
                package_name=pkg_data.get('name', 'Unknown Package'),
                price=Decimal(pkg_data.get('price', '0')),
            )

    logger.info(f"Food donation saved: {donation.reference_number} — ₹{donation.amount}")
    return donation


# ==================== EDUCATION FLOW HANDLERS ====================

def get_student_list_data():
    """Get active students for the STUDENT_LIST screen."""
    students = Student.objects.filter(is_active=True)

    student_options = [
        {
            'id': str(s.id),
            'title': f"{s.name} — {s.class_name}, {s.location}",
        }
        for s in students
    ]

    # Build info text for each student
    student_info = {}
    for s in students:
        student_info[str(s.id)] = (
            f"👤 *{s.name}*\n"
            f"📅 Age: {s.age}\n"
            f"🏫 School: {s.school}\n"
            f"📚 Class: {s.class_name}\n"
            f"📍 Location: {s.location}"
        )

    return {
        'screen': 'STUDENT_LIST',
        'data': {
            **_common_screen_data(),
            'student_options': student_options,
            'student_info': json.dumps(student_info),
        }
    }


def handle_student_select(data):
    """Process student selection and show amount screen."""
    student_id = data.get('selected_student', '')

    try:
        student = Student.objects.get(id=student_id, is_active=True)
    except Student.DoesNotExist:
        return get_student_list_data()

    amount_options = [
        {'id': '100', 'title': '₹100'},
        {'id': '500', 'title': '₹500'},
        {'id': '1000', 'title': '₹1,000'},
        {'id': '5000', 'title': '₹5,000'},
        {'id': '10000', 'title': '₹10,000'},
        {'id': 'custom', 'title': 'Custom Amount'},
    ]

    return {
        'screen': 'EDU_DONATION_AMOUNT',
        'data': {
            **_common_screen_data(),
            'student_id': str(student.id),
            'student_name': student.name,
            'student_info': (
                f"👤 {student.name}\n"
                f"📅 Age: {student.age}\n"
                f"🏫 {student.school}\n"
                f"📚 {student.class_name}\n"
                f"📍 {student.location}"
            ),
            'amount_options': amount_options,
        }
    }


def handle_edu_amount_submit(data):
    """Process amount selection and show donor info screen."""
    selected_amount = data.get('selected_amount', '')
    custom_amount = data.get('custom_amount', '')

    if selected_amount == 'custom' and custom_amount:
        amount = custom_amount
    elif selected_amount and selected_amount != 'custom':
        amount = selected_amount
    else:
        return handle_student_select(data)

    return {
        'screen': 'EDU_DONOR_INFO',
        'data': {
            **_common_screen_data(),
            'student_id': data.get('student_id', ''),
            'student_name': data.get('student_name', ''),
            'student_info': data.get('student_info', ''),
            'donation_amount': str(amount),
        }
    }


def handle_edu_donor_info_submit(data):
    """Process donor info and show review screen."""
    amount = data.get('donation_amount', '0')

    review_text = (
        f"📚 *Education Donation Review*\n\n"
        f"👤 Student: {data.get('student_name', '')}\n"
        f"💰 Amount: ₹{amount}\n\n"
        f"👤 Donor: {data.get('donor_name', '')}\n"
        f"✉️ Email: {data.get('donor_email', '')}\n"
        f"📱 WhatsApp: {data.get('donor_whatsapp', '')}"
    )

    return {
        'screen': 'EDU_REVIEW',
        'data': {
            **_common_screen_data(),
            'student_id': data.get('student_id', ''),
            'student_name': data.get('student_name', ''),
            'donor_name': data.get('donor_name', ''),
            'donor_email': data.get('donor_email', ''),
            'donor_whatsapp': data.get('donor_whatsapp', ''),
            'donor_instagram': data.get('donor_instagram', ''),
            'grand_total': str(amount),
            'review_text': review_text,
            'flow_type': 'EDUCATION',
        }
    }


def save_education_donation(data):
    """Save an education donation."""
    student_id = data.get('student_id', '')
    student = None
    if student_id:
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            pass

    donation = Donation.objects.create(
        whatsapp_phone_number=data.get('donor_whatsapp', ''),
        category='EDUCATION',
        cause='EDUCATION',
        amount=Decimal(data.get('grand_total', '0')),
        full_name=data.get('donor_name', ''),
        mobile_number=data.get('donor_whatsapp', ''),
        email=data.get('donor_email', ''),
        instagram_id=data.get('donor_instagram', ''),
        student=student,
        payment_status='PENDING',
    )

    if student:
        DonationItem.objects.create(
            donation=donation,
            item_type='STUDENT',
            item_name=student.name,
            item_id=student.id,
            quantity=1,
            unit_price=donation.amount,
            subtotal=donation.amount,
        )

    logger.info(f"Education donation saved: {donation.reference_number} — ₹{donation.amount}")
    return donation


# ==================== MEDICAL FLOW HANDLERS ====================

def get_patient_list_data():
    """Get active patients for the PATIENT_LIST screen."""
    patients = Patient.objects.filter(is_active=True)

    patient_options = [
        {
            'id': str(p.id),
            'title': f"{p.name} — ₹{p.raised_amount}/₹{p.goal_amount} ({p.progress_percent}%)",
        }
        for p in patients
    ]

    patient_info = {}
    for p in patients:
        patient_info[str(p.id)] = (
            f"👤 *{p.name}*\n"
            f"🏥 Hospital: {p.hospital}\n"
            f"📍 Location: {p.location}\n"
            f"💰 Raised: ₹{p.raised_amount:,.0f}\n"
            f"🎯 Goal: ₹{p.goal_amount:,.0f}\n"
            f"📊 Progress: {p.progress_percent}%"
        )

    return {
        'screen': 'PATIENT_LIST',
        'data': {
            **_common_screen_data(),
            'patient_options': patient_options,
            'patient_info': json.dumps(patient_info),
        }
    }


def handle_patient_select(data):
    """Process patient selection and show amount screen."""
    patient_id = data.get('selected_patient', '')

    try:
        patient = Patient.objects.get(id=patient_id, is_active=True)
    except Patient.DoesNotExist:
        return get_patient_list_data()

    amount_options = [
        {'id': '100', 'title': '₹100'},
        {'id': '500', 'title': '₹500'},
        {'id': '1000', 'title': '₹1,000'},
        {'id': '5000', 'title': '₹5,000'},
        {'id': '10000', 'title': '₹10,000'},
        {'id': 'custom', 'title': 'Custom Amount'},
    ]

    return {
        'screen': 'MED_DONATION_AMOUNT',
        'data': {
            **_common_screen_data(),
            'patient_id': str(patient.id),
            'patient_name': patient.name,
            'patient_info': (
                f"👤 {patient.name}\n"
                f"🏥 {patient.hospital}\n"
                f"📍 {patient.location}\n"
                f"💰 Raised: ₹{patient.raised_amount:,.0f}\n"
                f"🎯 Goal: ₹{patient.goal_amount:,.0f}\n"
                f"📊 Progress: {patient.progress_percent}%"
            ),
            'amount_options': amount_options,
        }
    }


def handle_med_amount_submit(data):
    """Process amount selection and show donor info screen."""
    selected_amount = data.get('selected_amount')
    custom_amount = data.get('custom_amount')
    amount = '0'

    if selected_amount == 'custom' and custom_amount:
        amount = custom_amount
    elif selected_amount and selected_amount != 'custom':
        amount = selected_amount
    else:
        return handle_patient_select(data)

    return {
        'screen': 'MED_DONOR_INFO',
        'data': {
            **_common_screen_data(),
            'patient_id': data.get('patient_id', ''),
            'patient_name': data.get('patient_name', ''),
            'patient_info': data.get('patient_info', ''),
            'donation_amount': str(amount),
        }
    }


def handle_med_donor_info_submit(data):
    """Process donor info and show review screen."""
    amount = data.get('donation_amount', '0')

    review_text = (
        f"🏥 *Medical Donation Review*\n\n"
        f"👤 Patient: {data.get('patient_name', '')}\n"
        f"💰 Amount: ₹{amount}\n\n"
        f"👤 Donor: {data.get('donor_name', '')}\n"
        f"✉️ Email: {data.get('donor_email', '')}\n"
        f"📱 WhatsApp: {data.get('donor_whatsapp', '')}"
    )

    return {
        'screen': 'MED_REVIEW',
        'data': {
            **_common_screen_data(),
            'patient_id': data.get('patient_id', ''),
            'patient_name': data.get('patient_name', ''),
            'donor_name': data.get('donor_name', ''),
            'donor_email': data.get('donor_email', ''),
            'donor_whatsapp': data.get('donor_whatsapp', ''),
            'donor_instagram': data.get('donor_instagram', ''),
            'grand_total': str(amount),
            'review_text': review_text,
            'flow_type': 'MEDICAL',
        }
    }


def save_medical_donation(data):
    """Save a medical donation and update patient raised amount."""
    patient_id = data.get('patient_id', '')
    patient = None
    amount = Decimal(data.get('grand_total', '0'))

    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            pass

    donation = Donation.objects.create(
        whatsapp_phone_number=data.get('donor_whatsapp', ''),
        category='MEDICAL',
        cause='MEDICAL',
        amount=amount,
        full_name=data.get('donor_name', ''),
        mobile_number=data.get('donor_whatsapp', ''),
        email=data.get('donor_email', ''),
        instagram_id=data.get('donor_instagram', ''),
        patient=patient,
        payment_status='PENDING',
    )

    if patient:
        DonationItem.objects.create(
            donation=donation,
            item_type='PATIENT',
            item_name=patient.name,
            item_id=patient.id,
            quantity=1,
            unit_price=amount,
            subtotal=amount,
        )

    logger.info(f"Medical donation saved: {donation.reference_number} — ₹{donation.amount}")
    return donation


# ==================== FOOD FORM HANDLERS ====================

def handle_food_form_screen(screen, data, flow_token):
    """Handle food donation form screen in flow endpoint"""
    if screen == 'food_donation_form':
        return {
            'screen': 'food_donation_form',
            'data': {
                **_common_screen_data(),
                'selected_food_item': data.get('selected_food_item', ''),
                'food_item_id': data.get('food_item_id', ''),
                'food_item_price': data.get('food_item_price', '100'),
                'food_item_unit': data.get('food_item_unit', 'Person'),
                'quantity': data.get('quantity', '1'),
                'total_amount': data.get('total_amount', '100'),
                'full_name': data.get('full_name', ''),
                'email': data.get('email', ''),
                'mobile_number': data.get('mobile_number', '')
            }
        }
    return None


def handle_food_form_complete(data, flow_token):
    """Handle food donation form completion"""
    try:
        # Create donation record
        donation = Donation.objects.create(
            whatsapp_phone_number=data.get('mobile_number', ''),
            category='FOOD',
            cause='FOOD',
            amount=Decimal(data.get('total_amount', '0')),
            full_name=data.get('full_name', ''),
            mobile_number=data.get('mobile_number', ''),
            email=data.get('email', ''),
            payment_status='PENDING',
        )
        
        # Create donation item
        DonationItem.objects.create(
            donation=donation,
            item_type='FOOD',
            item_name=data.get('selected_food_item', ''),
            item_id=int(data.get('food_item_id', 0)) if data.get('food_item_id') else 0,
            quantity=int(data.get('quantity', 1)),
            unit_price=Decimal(data.get('food_item_price', '0')),
            subtotal=Decimal(data.get('total_amount', '0')),
        )
        
        # Get payment URL
        redirect_url = get_payment_redirect_url(donation)
        
        return {
            'screen': 'SUCCESS',
            'data': {
                **_common_screen_data(),
                'extension_message_response': {
                    'params': {
                        'flow_token': flow_token,
                        'donation_reference': donation.reference_number,
                        'amount': str(donation.amount),
                        'payment_url': redirect_url,
                        'status': 'PAYMENT_INITIATED',
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in food form completion: {str(e)}")
        return {
            'screen': 'ERROR',
            'data': {
                **_common_screen_data(),
                'error_message': 'Failed to process donation. Please try again.',
                'extension_message_response': {
                    'params': {
                        'flow_token': flow_token,
                        'status': 'ERROR',
                        'error': str(e)
                    }
                }
            }
        }