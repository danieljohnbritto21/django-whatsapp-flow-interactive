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

def upload_flow():
    token = settings.WHATSAPP_TOKEN
    flow_id = settings.FLOW_ID
    json_path = os.path.join(settings.BASE_DIR, 'donation_flow.json')
    
    if not os.path.exists(json_path):
        print(f"Error: donation_flow.json not found at {json_path}")
        return
        
    print(f"Reading {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        flow_json_data = json.load(f)
        
    url = f"https://graph.facebook.com/v18.0/{flow_id}/assets"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # We must send name, asset_type and the file in multipart form-data.
    # Convert JSON back to string/bytes for file upload.
    flow_json_str = json.dumps(flow_json_data)
    
    files = {
        'file': ('flow.json', flow_json_str, 'application/json')
    }
    
    data = {
        'name': 'flow.json',
        'asset_type': 'FLOW_JSON'
    }
    
    print(f"Uploading to {url}...")
    response = requests.post(url, headers=headers, data=data, files=files)
    
    print(f"Status Code: {response.status_code}")
    try:
        res_json = response.json()
        print(json.dumps(res_json, indent=2))
    except Exception as e:
        print("Raw response:")
        print(response.text)

if __name__ == "__main__":
    upload_flow()
