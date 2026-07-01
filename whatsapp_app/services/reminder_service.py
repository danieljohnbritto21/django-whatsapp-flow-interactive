from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone
from whatsapp_app.messages import MESSAGES
from whatsapp_app.models import WhatsAppSession
from whatsapp_app.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)


class ReminderService:
    """
    Handles the logic for sending inactivity reminders to users.
    """

    # States where the user has completed or explicitly exited the flow.
    # Reminders should NOT be sent in these states.
    TERMINAL_STATES = {
        "COMPLETED",
        "PAYMENT_SUCCESS",
        "THANK_YOU",
        "CANCELLED",
        "NONE",
        "",
    }

    @staticmethod
    def _get_message(key: str, lang: str) -> str:
        """Helper to get a message string in the correct language."""
        return MESSAGES.get(lang, MESSAGES["en"]).get(key, key)

    @staticmethod
    def check_inactive_sessions():
        """
        Finds all active sessions that have been idle for more than 5 minutes
        and sends a single interactive reminder.
        """
        logger.info("[REMINDER] Checking for inactive sessions...")

        five_minutes_ago = timezone.now() - timedelta(minutes=5)

        # Find sessions that are:
        # 1. Active and haven't received a reminder yet.
        # 2. Last user interaction was over 5 minutes ago.
        # 3. Not in a terminal state where the conversation is considered complete.
        idle_sessions = WhatsAppSession.objects.filter(
            is_active=True,
            reminder_sent=False,
            last_interaction__lt=five_minutes_ago
        ).exclude(current_state__in=ReminderService.TERMINAL_STATES)

        logger.info(f"[REMINDER] Found {idle_sessions.count()} inactive sessions to remind.")

        for session in idle_sessions:
            lang = session.language or "en"
            logger.info(f"[REMINDER] Sending reminder to {session.whatsapp_phone_number} for session in state {session.current_state}.")

            whatsapp_service.send_interactive_buttons(
                session.whatsapp_phone_number,
                ReminderService._get_message("reminder_body_v2", lang),
                [
                    {"type": "reply", "reply": {"id": "continue_session", "title": ReminderService._get_message("continue_button_v2", lang)}},
                    {"type": "reply", "reply": {"id": "restart_session", "title": ReminderService._get_message("restart_button_v2", lang)}},
                ],
                header_text=ReminderService._get_message("reminder_header_v2", lang)
            )

            # Mark that a reminder has been sent to avoid spamming.
            session.reminder_sent = True
            session.save(update_fields=["reminder_sent"])
            logger.info(f"[REMINDER] Marked reminder as sent for {session.whatsapp_phone_number}.")