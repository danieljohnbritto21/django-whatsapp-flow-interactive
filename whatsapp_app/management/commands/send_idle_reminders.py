from django.core.management.base import BaseCommand
from django.utils import timezone
from whatsapp_app.models import WhatsAppSession
from whatsapp_app.whatsapp_service import whatsapp_service
from whatsapp_app.messages import MESSAGES

class Command(BaseCommand):
    help = 'Sends reminders to users who have been idle in a conversation for more than 1 minute.'

    def handle(self, *args, **options):
        self.stdout.write(f"[{timezone.now()}] Running send_idle_reminders command...")

        # Find sessions that are idle, not in a final state, and haven't had a reminder sent.
        idle_sessions = WhatsAppSession.objects.exclude(
            current_state__in=["MENU", "LANGUAGE_SELECT"]
        ).filter(
            reminder_sent=False
        )

        sent_count = 0
        for session in idle_sessions:
            if session.is_idle(minutes=1):
                try:
                    lang = getattr(session, 'language', 'en')  # Safely get language, default to 'en'
                    reminder_message = MESSAGES.get(lang, MESSAGES["en"]).get("idle_reminder")
                    whatsapp_service.send_text_message(session.whatsapp_phone_number, reminder_message)
                    session.mark_reminder_sent()
                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Sent reminder to {session.whatsapp_phone_number}"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to send reminder to {session.whatsapp_phone_number}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Finished. Sent {sent_count} reminders."))