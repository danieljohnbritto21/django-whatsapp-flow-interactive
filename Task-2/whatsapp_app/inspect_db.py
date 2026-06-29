import os
import django
import sys

# Setup Django environment
sys.path.append('d:/Task-2')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsapp_project.settings')
django.setup()

from whatsapp_app.models import WhatsAppWebhookLog, Donation
import json

def inspect_db():
    print("--- LATEST WEBHOOK LOGS ---")
    logs = WhatsAppWebhookLog.objects.all().order_by('-created_at')[:5]
    for log in logs:
        print(f"ID: {log.webhook_id}, Processed: {log.processed}, Created: {log.created_at}")
        # Print only messages info to keep it brief
        val = log.payload.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {})
        messages = val.get('messages', [])
        if messages:
            print(f"  Messages: {json.dumps(messages, indent=2)}")
        else:
            print("  No messages in payload")

    print("\n--- LATEST DONATIONS ---")
    donations = Donation.objects.all().order_by('-created_at')[:5]
    for d in donations:
        print(f"Ref: {d.reference_number}, Name: {d.full_name}, Phone: {d.whatsapp_phone_number}, Amount: {d.amount}, Status: {d.payment_status}")

if __name__ == "__main__":
    inspect_db()
