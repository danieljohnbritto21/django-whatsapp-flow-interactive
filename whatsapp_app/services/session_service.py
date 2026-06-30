from __future__ import annotations

from typing import Any, Dict, Optional

from whatsapp_app.models import WhatsAppSession


class SessionService:
    @staticmethod
    def get_or_create(phone_number: str) -> WhatsAppSession:
        session, _ = WhatsAppSession.objects.get_or_create(
            whatsapp_phone_number=phone_number,
            defaults={"current_state": "MENU", "session_data": {}},
        )
        return session

    @staticmethod
    def update_state(session: WhatsAppSession, state: str) -> None:
        session.current_state = state
        session.save(update_fields=["current_state", "last_interaction", "session_data"])

    @staticmethod
    def set_language(session: WhatsAppSession, lang_code: str) -> None:
        session.language = lang_code
        session.save(update_fields=["language", "last_interaction"])

    @staticmethod
    def set_data(session: WhatsAppSession, key: str, value: Any) -> None:
        data: Dict[str, Any] = session.session_data or {}
        data[key] = value
        session.session_data = data
        session.save(update_fields=["session_data", "last_interaction"])

    @staticmethod
    def clear(session: WhatsAppSession) -> None:
        session.current_state = "MENU"
        session.session_data = {}
        session.reminder_sent = False
        session.save(update_fields=["current_state", "session_data", "last_interaction"])
