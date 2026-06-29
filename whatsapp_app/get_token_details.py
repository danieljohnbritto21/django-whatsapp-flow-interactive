import os
import django
import sys

# Setup Django environment
sys.path.append('d:/Task-2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_project.settings')
django.setup()

from django.conf import settings
import requests
import json

def get_details():
    token = settings.WHATSAPP_TOKEN
    phone_id = settings.PHONE_NUMBER_ID
    flow_id = settings.FLOW_ID
    
    headers = {
        'Authorization': f'Bearer {token}',
    }
    
    print("=== QUERYING ME ENDPOINT ===")
    me_url = "https://graph.facebook.com/v18.0/me"
    r = requests.get(me_url, headers=headers)
    print(f"Me status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    
    # Try querying businesses owned or shared
    print("\n=== QUERYING BUSINESSES ===")
    r = requests.get(f"{me_url}/businesses", headers=headers)
    print(f"Businesses status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))

    # Try querying WhatsApp Business Accounts
    print("\n=== QUERYING OWNED WHATSAPP BUSINESS ACCOUNTS ===")
    # Note: we need a business ID to query owned_whatsapp_business_accounts,
    # but we can try to query me/accounts (which returns pages/accounts)
    r = requests.get(f"{me_url}/accounts", headers=headers)
    print(f"Accounts status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    
    # Let's see if we can get app details by querying client token or app id
    # Many times we can query GET /v18.0/app to see the app details
    print("\n=== QUERYING APP DETAILS ===")
    r = requests.get("https://graph.facebook.com/v18.0/app", headers=headers)
    print(f"App status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    
    # Let's inspect the phone number details in detail
    print("\n=== QUERYING PHONE NUMBER DETAIL FIELDS ===")
    # Fields: display_phone_number, verified_name, quality_rating, code_verification_status, name_status, is_pin_enabled, is_official_business_account
    r = requests.get(f"https://graph.facebook.com/v18.0/{phone_id}?fields=display_phone_number,verified_name,quality_rating,code_verification_status,name_status,is_pin_enabled,is_official_business_account,platform_type,throughput", headers=headers)
    print(f"Phone details status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    get_details()
