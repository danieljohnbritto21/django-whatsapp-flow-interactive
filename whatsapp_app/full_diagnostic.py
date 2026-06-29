"""
Comprehensive Meta API Diagnostic Script
Checks every layer that can trigger #139000 Blocked by Integrity
"""
import os
import sys
import json
import requests

sys.path.append('d:/Task-2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_project.settings')

import django
django.setup()

from django.conf import settings

TOKEN = settings.WHATSAPP_TOKEN
PHONE_ID = settings.PHONE_NUMBER_ID
FLOW_ID = settings.FLOW_ID
BASE = "https://graph.facebook.com/v23.0"

headers = {"Authorization": f"Bearer {TOKEN}"}

def api(method, url, **kwargs):
    fn = requests.get if method == "GET" else requests.post
    r = fn(url, headers=headers, **kwargs)
    try:
        json_response = r.json()
    except requests.exceptions.JSONDecodeError:
        # If the response is not JSON, return the raw text.
        json_response = {'error': 'Not a JSON response', 'text': r.text}
    return r.status_code, json_response

print("=" * 70)
print("META API DIAGNOSTIC - WhatsApp Flow Integrity Block")
print("=" * 70)

# 1. Token validity + identity
print("\n[1] TOKEN IDENTITY (GET /me)")
s, d = api("GET", f"{BASE}/me")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 2. App details
print("\n[2] APP DETAILS (GET /app)")
s, d = api("GET", f"{BASE}/app")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 3. Phone number details - ALL fields
print(f"\n[3] PHONE NUMBER DETAILS (GET /{PHONE_ID})")
fields = ",".join([
    "display_phone_number", "verified_name", "quality_rating",
    "code_verification_status", "name_status", "is_pin_enabled",
    "is_official_business_account", "platform_type", "throughput",
    "status", "messaging_limit_tier", "certificate"
])
s, d = api("GET", f"{BASE}/{PHONE_ID}?fields={fields}")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 4. WABA details - using the ID from user's findings
WABA_ID = "1493686071844979"
print(f"\n[4] WABA DETAILS (GET /{WABA_ID})")
waba_fields = "id,name,account_review_status,on_behalf_of_business_info,primary_funding_id,purchase_order_number,timezone_id"
s, d = api("GET", f"{BASE}/{WABA_ID}?fields={waba_fields}")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 5. WABA health status
print(f"\n[5] WABA HEALTH STATUS")
s, d = api("GET", f"{BASE}/{WABA_ID}?fields=account_review_status,ban_info,violation_info")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 6. Flow details
print(f"\n[6] FLOW DETAILS (GET /{FLOW_ID})")
flow_fields = "id,name,status,categories,validation_errors,json_version,data_api_version,endpoint_uri,preview,whatsapp_business_account,application"
s, d = api("GET", f"{BASE}/{FLOW_ID}?fields={flow_fields}")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 7. List all flows in WABA
print(f"\n[7] ALL FLOWS IN WABA (GET /{WABA_ID}/flows)")
s, d = api("GET", f"{BASE}/{WABA_ID}/flows")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 8. Business verification - try to get business info
print(f"\n[8] BUSINESS INFO FROM WABA")
s, d = api("GET", f"{BASE}/{WABA_ID}?fields=on_behalf_of_business_info")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 9. Test: send a simple text message (should work per user)
print(f"\n[9] TEST: SEND TEXT MESSAGE")
text_payload = {
    "messaging_product": "whatsapp",
    "to": "919345655206",
    "type": "text",
    "text": {"body": "Diagnostic test message"}
}
s, d = api("POST", f"{BASE}/{PHONE_ID}/messages", json=text_payload)
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 10. Test: send the EXACT flow payload that fails
print(f"\n[10] TEST: SEND FLOW MESSAGE (EXPECTED TO FAIL WITH 139000)")
flow_payload = {
    "messaging_product": "whatsapp",
    "to": "919345655206",
    "type": "interactive",
    "interactive": {
        "type": "flow",
        "header": {"type": "text", "text": "Donate to Thaagam Foundation"},
        "body": {"text": "Please click the button below to choose your donation options."},
        "action": {
            "name": "flow",
            "parameters": {
                "flow_cta": "Donate Now",
                "flow_message_version": "3",
                "flow_token": "diag_test_food_001",
                "flow_id": FLOW_ID,
                "flow_action": "navigate",
                "flow_action_payload": {
                    "screen": "collect_purchase_interest",
                    "data": {
                        "food_qty": "1",
                        "donor_name": "",
                        "donor_email": "",
                        "donor_whatsapp": "919345655206",
                    }
                },
                "mode": "draft"
            }
        }
    }
}
s, d = api("POST", f"{BASE}/{PHONE_ID}/messages", json=flow_payload)
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 11. Test: try publishing the flow
print(f"\n[11] TEST: PUBLISH FLOW (POST /{FLOW_ID}/publish)")
s, d = api("POST", f"{BASE}/{FLOW_ID}/publish")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 12. Check phone number registered status with WABA
print(f"\n[12] PHONE NUMBERS IN WABA")
s, d = api("GET", f"{BASE}/{WABA_ID}/phone_numbers?fields=display_phone_number,verified_name,code_verification_status,quality_rating,status,is_official_business_account,name_status")
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

# 13. Check if our API version matters
print(f"\n[13] TEST: SEND FLOW VIA v18.0 (CURRENT CODE PATH)")
old_base = "https://graph.facebook.com/v18.0"
s, d = api("POST", f"{old_base}/{PHONE_ID}/messages", json=flow_payload)
print(f"    Status: {s}")
print(f"    Response: {json.dumps(d, indent=4)}")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
