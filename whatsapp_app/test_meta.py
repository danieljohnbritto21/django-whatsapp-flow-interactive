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

def test_meta_api():
    token = settings.WHATSAPP_TOKEN
    phone_id = settings.PHONE_NUMBER_ID
    flow_id = settings.FLOW_ID
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print("--- 1. Querying App/Token Debug Info ---")
    debug_url = f"https://graph.facebook.com/debug_token?input_token={token}"
    # Note: debug_token requires an app access token or admin token, so it might fail, but let's try.
    response = requests.get(f"https://graph.facebook.com/v18.0/me?access_token={token}")
    print(f"Me Endpoint Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    print("\n--- 2. Querying Phone Number ID ---")
    phone_url = f"https://graph.facebook.com/v18.0/{phone_id}"
    response = requests.get(phone_url, headers=headers)
    print(f"Phone Number Status: {response.status_code}")
    phone_data = response.json()
    print(json.dumps(phone_data, indent=2))
    
    # Try to find WABA ID from phone number fields if available
    waba_id = phone_data.get('whatsapp_business_account', {}).get('id')
    if not waba_id:
        # Let's request it specifically
        response = requests.get(f"{phone_url}?fields=whatsapp_business_account", headers=headers)
        waba_data = response.json()
        print("WABA specific query:")
        print(json.dumps(waba_data, indent=2))
        waba_id = waba_data.get('whatsapp_business_account', {}).get('id')

    print(f"\nResolved WABA ID: {waba_id}")
    
    print(f"\n--- 3. Querying Flow {flow_id} ---")
    flow_url = f"https://graph.facebook.com/v18.0/{flow_id}"
    response = requests.get(flow_url, headers=headers)
    print(f"Flow Status: {response.status_code}")
    flow_data = response.json()
    print(json.dumps(flow_data, indent=2))
    
    if waba_id:
        print(f"\n--- 4. Listing Flows in WABA {waba_id} ---")
        flows_list_url = f"https://graph.facebook.com/v18.0/{waba_id}/flows"
        response = requests.get(flows_list_url, headers=headers)
        print(f"List Flows Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_meta_api()
