from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from whatsapp_app.services.chatbot import handle_interactive_selection, handle_text_message
from whatsapp_app.services.session_service import SessionService


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

    return "unsupported", ""


@csrf_exempt
def webhook_handler(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)

    payload = json.loads(request.body or b"{}")

    print("=" * 60)
    print("[WEBHOOK] RECEIVED")
    print(f"[WEBHOOK] RAW REQUEST BODY: {request.body[:500] if request.body else 'EMPTY'}")
    print(f"[WEBHOOK] INCOMING JSON PAYLOAD: {json.dumps(payload)[:500] if payload else 'EMPTY'}")

    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value", {}) or {}

            for message in value.get("messages", []) or []:
                phone_number = message.get("from")
                if not phone_number:
                    continue

                print(f"[PHONE] {phone_number}")

                session = SessionService.get_or_create(phone_number)

                # Debug: capture parsing correctness for numeric validation issues
                current_state = session.current_state
                print(f"[SESSION] CURRENT STATE: {current_state}")
                print(f"[SESSION] EXPECTED (for FOOD qty): FOOD_FORM_QUANTITY")
                print(f"[MESSAGE] TYPE: {message.get('type')}")
                print(f"[MESSAGE] RAW: {repr(message)}")

                msg_kind, content = _parse_message(message)
                print(f"[PARSE] MSG_KIND: {msg_kind}")
                print(f"[PARSE] CONTENT: {repr(content)}")

                if msg_kind == "text":
                    # For numeric validation steps, ONLY use text body
                    print(f"[ROUTE] CALLING handle_text_message")
                    print(f"[ROUTE] ARGUMENT: {repr((content or '').strip())}")
                    handle_text_message(phone_number, (content or "").strip(), session)
                elif msg_kind == "interactive":
                    print(f"[ROUTE] CALLING handle_interactive_selection")
                    handle_interactive_selection(phone_number, content or "", session)
                else:
                    # ignore
                    pass

    return HttpResponse(json.dumps({"status": "success"}), content_type="application/json", status=200)

