from __future__ import annotations

import json
import logging
from typing import Any, Dict, Tuple

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from whatsapp_app.services.chatbot import (
    handle_interactive_selection,
    handle_location_message,
    handle_text_message,
)
from whatsapp_app.services.session_service import SessionService

logger = logging.getLogger(__name__)


def _parse_message(message: Dict[str, Any]) -> Tuple[str, str]:
    msg_type = message.get("type", "text")

    if msg_type == "text":
        body = message.get("text", {}).get("body", "")
        return "text", body

    if msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return "interactive", interactive.get("button_reply", {}).get("id", "")
        if interactive.get("type") == "list_reply":
            return "interactive", interactive.get("list_reply", {}).get("id", "")

    if msg_type == "location":
        return "location", message.get("location", {})

    # This part was already added in the previous turn, but I'll ensure logging is consistent.
    # The requirement explicitly states to ignore statuses.
    if message.get("statuses"):
        return "status", ""

    return "unsupported", ""


@csrf_exempt
def webhook_handler(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = json.loads(request.body or b"{}")
    logger.debug(f"[WEBHOOK] Incoming payload: {json.dumps(payload)}")

    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}

            # Handle status updates separately from messages
            if "statuses" in value:
                for status in value.get("statuses", []):
                    logger.info(f"[WEBHOOK] Ignored status event: {status.get('status')} for {status.get('recipient_id')}")
                continue

            # Handle incoming messages
            for message in value.get("messages", []) or []:
                phone_number = message.get("from")
                if not phone_number:
                    logger.warning("[WEBHOOK] Message received without a 'from' number.")
                    continue

                logger.info(f"[WEBHOOK] Processing message from {phone_number}")

                session = SessionService.get_or_create(phone_number)
                logger.info(f"[WEBHOOK] Session for {phone_number} in state: {session.current_state}")

                msg_kind, content = _parse_message(message)

                if msg_kind == "text":
                    logger.info(f"[WEBHOOK] Incoming Text Message from {phone_number}: '{content}'")
                    handle_text_message(phone_number, (content or "").strip(), session)

                elif msg_kind == "interactive":
                    logger.info(f"[WEBHOOK] Incoming Interactive Reply from {phone_number}: ID='{content}'")
                    handle_interactive_selection(phone_number, content or "", session)

                elif msg_kind == "location":
                    logger.info(f"[WEBHOOK] Incoming Location Message from {phone_number}")
                    handle_location_message(phone_number, content or {}, session)

                elif msg_kind == "status":
                    # Already handled above, but we log here for clarity if logic changes
                    pass

                else:
                    logger.warning(f"[WEBHOOK] Ignored unsupported message type '{message.get('type')}' from {phone_number}.")

    return HttpResponse(json.dumps({"status": "success"}), content_type="application/json", status=200)
