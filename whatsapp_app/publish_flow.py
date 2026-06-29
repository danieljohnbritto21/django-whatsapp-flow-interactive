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

def publish_flow():
    token = settings.WHATSAPP_TOKEN
    flow_id = settings.FLOW_ID
    
    url = f"https://graph.facebook.com/v18.0/{flow_id}/publish"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print(f"Attempting to publish Flow {flow_id}...")
    response = requests.post(url, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    try:
        res_json = response.json()
        print(json.dumps(res_json, indent=2))
    except Exception as e:
        print("Raw response:")
        print(response.text)

if __name__ == "__main__":
    publish_flow()
