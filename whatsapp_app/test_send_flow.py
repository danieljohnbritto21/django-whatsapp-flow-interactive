import os
import django
import sys
import uuid

# Setup Django environment
sys.path.append('d:/Task-2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_project.settings')
django.setup()

from django.conf import settings
import requests
import json

def test_send_flow(cta_text, to_phone="919345655206"):
    token = settings.WHATSAPP_TOKEN
    phone_id = settings.PHONE_NUMBER_ID
    flow_id = settings.FLOW_ID
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    flow_token = f"flow_test_{uuid.uuid4().hex[:8]}"
    
    interactive_data = {
        'type': 'flow',
        'action': {
            'name': 'flow',
            'parameters': {
                'flow_cta': cta_text,
                'flow_message_version': '3',
                'flow_token': flow_token,
                'flow_id': flow_id,
                'flow_action': 'data_exchange',
                'mode': getattr(settings, 'FLOW_MODE', 'draft'),
            }
        },
        'header': {
            'type': 'text',
            'text': 'Donate to Thaagam Foundation'
        },
        'body': {
            'text': 'Please click the button below to choose your donation options.'
        },
        'footer': {
            'text': 'Thaagam Foundation'
        }
    }
    
    data = {
        'messaging_product': 'whatsapp',
        'to': to_phone,
        'type': 'interactive',
        'interactive': interactive_data
    }
    
    print(f"Sending flow message to {to_phone} with CTA: '{cta_text}'...")
    response = requests.post(url, headers=headers, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    # Test sending with the clean CTA text
    test_send_flow("Donate Now")
