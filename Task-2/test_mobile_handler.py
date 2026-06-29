#!/usr/bin/env python
"""
Quick test for mobile number handler
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_project.settings')
django.setup()

from whatsapp_app.models import WhatsAppSession
from whatsapp_app.views import handle_food_form_mobile
from whatsapp_app.whatsapp_service import whatsapp_service

def test_mobile_handler():
    print("Testing mobile number handler...")
    
    # Create test session with sample data
    phone_number = "919876543210"
    session, created = WhatsAppSession.objects.get_or_create(
        whatsapp_phone_number=phone_number,
        defaults={
            'current_state': 'FOOD_FORM_MOBILE',
            'session_data': {
                'selected_food_item': {
                    'id': 1,
                    'name': 'Feed a Homeless Person',
                    'price': 30.0,
                    'unit_label': 'Person'
                },
                'quantity': 5,
                'total_amount': 150.0,
                'full_name': 'Test User',
                'email': 'test@example.com'
            }
        }
    )
    
    if not created:
        session.current_state = 'FOOD_FORM_MOBILE'
        session.session_data = {
            'selected_food_item': {
                'id': 1,
                'name': 'Feed a Homeless Person',
                'price': 30.0,
                'unit_label': 'Person'
            },
            'quantity': 5,
            'total_amount': 150.0,
            'full_name': 'Test User',
            'email': 'test@example.com'
        }
        session.save()
    
    print(f"Session created: {session}")
    print(f"Session data: {session.session_data}")
    
    # Test mobile number input
    try:
        handle_food_form_mobile(phone_number, session, "9876543210")
        
        # Refresh session from database
        session.refresh_from_db()
        print(f"After mobile input - State: {session.current_state}")
        print(f"Session data: {session.session_data}")
        
        if session.current_state == 'PAYMENT_OR_PACKAGES_CHOICE':
            print("✅ SUCCESS: Mobile handler worked correctly!")
            print("✅ State changed to PAYMENT_OR_PACKAGES_CHOICE")
            print("✅ Should show payment/packages choice buttons")
        else:
            print(f"❌ FAILURE: Expected state PAYMENT_OR_PACKAGES_CHOICE, got {session.current_state}")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mobile_handler()