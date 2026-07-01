import logging
import time

from django.core.management.base import BaseCommand
from whatsapp_app.scheduler import send_idle_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the background scheduler to check for idle WhatsApp sessions."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting WhatsApp session scheduler..."))
        logger.info("Scheduler started.")

        while True:
            try:
                send_idle_reminders()
            except Exception as e:
                logger.exception("An error occurred in the scheduler loop.")
                self.stderr.write(self.style.ERROR(f"Scheduler error: {e}"))
            
            # Run the check every 60 seconds.
            # This is a simple polling mechanism suitable for this task.
            # For more complex needs, consider libraries like APScheduler or Celery Beat.
            time.sleep(60)