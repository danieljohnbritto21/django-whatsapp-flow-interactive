import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

from whatsapp_app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)


def start():
    """
    Start the background scheduler.

    Runs the inactivity reminder job every 10 seconds.
    Prevents duplicate schedulers caused by Django's auto-reloader.
    """

    # Prevent duplicate scheduler during development
    if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
        return

    # Don't start twice
    if scheduler.running:
        logger.info("[SCHEDULER] Scheduler already running.")
        return

    # Register the reminder job only once
    if scheduler.get_job("check_inactive_sessions") is None:
        scheduler.add_job(
            func=ReminderService.check_inactive_sessions,
            trigger="interval",
            seconds=10,              # Check every 10 seconds
            id="check_inactive_sessions",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )

        logger.info("[SCHEDULER] Reminder job registered.")

    try:
        logger.info("[SCHEDULER] Starting BackgroundScheduler...")
        scheduler.start()
        logger.info("[SCHEDULER] BackgroundScheduler started successfully.")
    except Exception:
        logger.exception("[SCHEDULER] Failed to start BackgroundScheduler.")


def stop():
    """
    Stop the scheduler gracefully.
    """
    if scheduler.running:
        logger.info("[SCHEDULER] Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Scheduler stopped.")