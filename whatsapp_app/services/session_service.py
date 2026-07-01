from __future__ import annotations

import logging
from typing import Any, Dict

from whatsapp_app.models import WhatsAppSession
from django.utils import timezone

logger = logging.getLogger(__name__)


class SessionService:
    """
    Manages the lifecycle of a WhatsApp user session, including creation,
    state updates, data storage, and idle management.
    """

    @staticmethod
    def get_or_create(phone_number: str) -> WhatsAppSession:
        session, _ = WhatsAppSession.objects.get_or_create(
            whatsapp_phone_number=phone_number.strip(),
            defaults={"current_state": "MENU", "session_data": {}, "last_interaction": timezone.now()},
        )
        # Update last_interaction and reset reminder on any incoming user activity.
        if session.reminder_sent:
            session.reminder_sent = False
        session.last_interaction = timezone.now()
        session.save(update_fields=["last_interaction", "reminder_sent"])
        return session

    @staticmethod
    def update_state(session: WhatsAppSession, state: str) -> None:
        session.current_state = state.upper()
        session.last_interaction = timezone.now()
        session.save(update_fields=["current_state", "last_interaction"])

    @staticmethod
    def set_language(session: WhatsAppSession, lang_code: str) -> None:
        session.language = lang_code
        session.last_interaction = timezone.now()
        session.save(update_fields=["language", "last_interaction"])

    @staticmethod
    def set_data(session: WhatsAppSession, key: str, value: Any) -> None:
        data: Dict[str, Any] = session.session_data or {}
        data[key] = value
        session.session_data = data
        session.last_interaction = timezone.now()
        session.save(update_fields=["session_data", "last_interaction"])

    @staticmethod
    def clear(session: WhatsAppSession) -> None:
        """Resets the session to its initial state, clearing all data."""
        session.current_state = "MENU" # This will trigger language selection on next message
        session.language = "en" # Reset language
        session.session_data = {}
        session.reminder_sent = False
        session.save(
            update_fields=[
                "current_state",
                "session_data",
                "reminder_sent",
                "language",
                "last_interaction",
            ]
        )

    @staticmethod
    def mark_reminder_sent(session: WhatsAppSession) -> None:
        """Marks that an idle reminder has been sent for this session."""
        # This is now handled directly in reminder_service.py for clarity
        session.reminder_sent = True
        session.save(update_fields=["reminder_sent"])

    @staticmethod
    def reset_reminder_sent(session: WhatsAppSession) -> None:
        """Resets the reminder flag, typically upon receiving any user message."""
        # This is now handled centrally in get_or_create
        if session.reminder_sent:
            session.reminder_sent = False # Only change the flag
            session.save(update_fields=["reminder_sent"])
        # last_interaction is updated separately to ensure it always happens on user activity

    @staticmethod
    def resume_session(session: WhatsAppSession) -> None:
        """
        Resumes a session by re-sending the prompt for the current state.
        This is used when a user chooses to 'Continue' after an idle reminder.
        """
        # Local imports to prevent circular dependencies
        from whatsapp_app.services.chatbot import (
            send_donation_review,
            _send_food_quantity_prompt,
            _send_edu_amount_prompt,
            _send_med_amount_prompt,
            _send_instagram_prompt,
        )
        from whatsapp_app.services.message_service import (
            send_donate_category_menu,
            send_location_request,
            send_menu,
        )
        from whatsapp_app.services.interactive_service import (
            send_food_items_list,
            send_optional_packages,
            send_patient_list,
            send_student_list,
        )
        from whatsapp_app.services.payment_service import send_pay_now_cta
        from whatsapp_app.whatsapp_service import whatsapp_service # Correct
        from whatsapp_app.messages import MESSAGES # Correct
        
        logger.info(f"[CONTINUE] Resuming session for {session.whatsapp_phone_number} at state {session.current_state}")

        lang = session.language or "en"
        state = session.current_state
        data = session.session_data or {}

        def _get_message(key, **kwargs):
            message = MESSAGES.get(lang, MESSAGES["en"]).get(key, key)
            return message.format(**kwargs) if kwargs else message

        STATE_PROMPT_MAP = {
            "MAIN_MENU": lambda: send_menu(session.whatsapp_phone_number, lang),
            "CATEGORY_SELECT": lambda: send_donate_category_menu(session.whatsapp_phone_number, lang),
            "FOOD_ITEM_SELECT": lambda: send_food_items_list(session.whatsapp_phone_number, lang),
            "FOOD_FORM_QUANTITY": lambda: _send_food_quantity_prompt(session),
            "FOOD_FORM_FULL_NAME": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_full_name")),
            "FOOD_FORM_EMAIL": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_email")),
            "FOOD_FORM_MOBILE": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_mobile")),
            "FOOD_FORM_INSTAGRAM": lambda: _send_instagram_prompt(session),
            "EDU_STUDENT_SELECT": lambda: send_student_list(session.whatsapp_phone_number, lang),
            "EDU_STUDENT_SELECTED_AMOUNT": lambda: _send_edu_amount_prompt(session),
            "EDU_FORM_FULL_NAME": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_full_name")),
            "EDU_FORM_EMAIL": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_email")),
            "EDU_FORM_MOBILE": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_mobile")),
            "EDU_FORM_INSTAGRAM": lambda: _send_instagram_prompt(session),
            "MED_PATIENT_SELECT": lambda: send_patient_list(session.whatsapp_phone_number, lang),
            "MED_PATIENT_SELECTED_AMOUNT": lambda: _send_med_amount_prompt(session),
            "MED_FORM_FULL_NAME": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_full_name")),
            "MED_FORM_EMAIL": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_email")),
            "MED_FORM_MOBILE": lambda: whatsapp_service.send_text_message(session.whatsapp_phone_number, _get_message("ask_mobile")),
            "MED_FORM_INSTAGRAM": lambda: _send_instagram_prompt(session),
            "AWAITING_LOCATION": lambda: send_location_request(session.whatsapp_phone_number, lang),
            # Review states will re-trigger the review generation
            "FOOD_REVIEW": lambda: send_donation_review(session.whatsapp_phone_number, session),
            "EDU_REVIEW": lambda: send_donation_review(session.whatsapp_phone_number, session),
            "MED_REVIEW": lambda: send_donation_review(session.whatsapp_phone_number, session),
        }

        prompt_function = STATE_PROMPT_MAP.get(state)
        if prompt_function:
            prompt_function()
            logger.info(f"[CONTINUE] Successfully re-sent prompt for state {state} to {session.whatsapp_phone_number}.")
        else:
            logger.warning(f"[CONTINUE] No specific resume action for state {state} for {session.whatsapp_phone_number}. Sending generic prompt.")
            continue_message = _get_message("continue_flow")
            whatsapp_service.send_text_message(session.whatsapp_phone_number, continue_message)

        session.last_interaction = timezone.now()
        session.save(update_fields=["last_interaction"])
