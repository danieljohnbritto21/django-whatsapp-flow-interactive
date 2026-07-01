import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from whatsapp_app.models import WhatsAppSession
from whatsapp_app.services.session_service import SessionService
from whatsapp_app.messages import MESSAGES

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sends reminders to users who have been idle in a conversation for more than 5 minutes.'

    def handle(self, *args, **options):
        self.stdout.write(f"[{timezone.now()}] Running send_idle_reminders command for 5-minute idle check...")
        logger.info("[IDLE REMINDER] Starting idle reminder check.")

        from whatsapp_app.whatsapp_service import whatsapp_service
        
        # Define the idle threshold
        idle_threshold = timezone.now() - timedelta(minutes=5)

        # Find sessions that are idle, not in a final state, and haven't had a reminder sent.
        idle_sessions = WhatsAppSession.objects.exclude(
            current_state__in=["MENU", "LANGUAGE_SELECT"]
        ).filter(
            is_active=True,
            reminder_sent=False,
            last_interaction__lt=idle_threshold
        )

        sent_count = 0
        if not idle_sessions.exists():
            logger.info("[IDLE REMINDER] No idle sessions found meeting the criteria.")
            self.stdout.write("No idle sessions to process.")
            return

        for session in idle_sessions:
            try:
                idle_minutes = (timezone.now() - session.last_interaction).total_seconds() / 60
                logger.info(f"[IDLE REMINDER] Phone: {session.whatsapp_phone_number}, State: {session.current_state}, Idle: {idle_minutes:.2f} mins. Sending reminder.")
                
                lang = getattr(session, 'language', 'en')
                messages = MESSAGES.get(lang, MESSAGES["en"])

                whatsapp_service.send_interactive_buttons(
                    to_phone_number=session.whatsapp_phone_number,
                    body_text=messages.get("idle_reminder_body"),
                    buttons=[
                        {"type": "reply", "reply": {"id": "continue_session", "title": messages.get("continue_button")}},
                        {"type": "reply", "reply": {"id": "restart_session", "title": messages.get("restart_button")}},
                    ],
                    header_text=messages.get("idle_reminder_header"),
                )
                SessionService.mark_reminder_sent(session)
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f"Sent reminder to {session.whatsapp_phone_number}"))
                logger.info(f"[IDLE REMINDER] Reminder sent to {session.whatsapp_phone_number}.")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to send reminder to {session.whatsapp_phone_number}: {e}"))
                logger.exception(f"[IDLE REMINDER] Failed to send reminder to {session.whatsapp_phone_number}")

        if sent_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Finished. Sent {sent_count} reminders."))
            logger.info(f"Idle reminder check finished. Sent {sent_count} reminders.")
        else:
            self.stdout.write("Finished. No reminders sent as no sessions met the 5-minute idle time criteria.")
            logger.info("Idle reminder check finished. No sessions met the 5-minute idle criteria.")