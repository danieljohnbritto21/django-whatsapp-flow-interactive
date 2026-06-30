from __future__ import annotations

from django.conf import settings
from whatsapp_app.messages import MESSAGES
from decimal import Decimal
from typing import Optional

from whatsapp_app.models import FoodItem, Package, Patient, Student, Donation
from whatsapp_app.services.donation_service import DonationService
from whatsapp_app.services.interactive_service import (
    parse_package_selection,
    send_food_items_list,
    send_optional_packages,
    send_patient_list,
    send_student_list,
)
from whatsapp_app.services.message_service import (
    send_location_request,
    send_contact,
    send_donate_category_menu,
    send_location,
    send_menu,
)
from whatsapp_app.services.validation_service import send_validation_errors
from whatsapp_app.services.payment_service import send_pay_now_cta
from whatsapp_app.services.session_service import SessionService
from whatsapp_app.services.utils import extract_digits, normalize_command, safe_decimal
from whatsapp_app.whatsapp_service import whatsapp_service


def _state_category(state: str) -> Optional[str]:
    # FIX: previously returned "EDUCATION" / "MEDICAL", which do NOT match the
    # actual state-name prefixes used throughout this file ("EDU_" / "MED_").
    # That mismatch caused f"{current_flow_prefix}_FORM_INSTAGRAM" to build an
    # invalid state name (e.g. "EDUCATION_FORM_INSTAGRAM") whenever a user
    # tapped the "Enter" button on the Instagram ID prompt for Education or
    # Medical, silently breaking that path.
    if state.startswith("FOOD_"):
        return "FOOD"
    if state.startswith("EDU_"):
        return "EDU"
    if state.startswith("MED_"):
        return "MED"
    return None


def handle_location_message(phone_number: str, location_data: dict, session) -> None:
    """Handles incoming location messages from the user."""
    # For now, we just log it. You can save it to the user's profile or donation record.
    print(f"[LOCATION] Received from {phone_number}: {location_data}")

    # If we are awaiting a location, process it and proceed to the review step.
    if session.current_state == "AWAITING_LOCATION":
        session.session_data["location"] = location_data
        session.save(update_fields=["session_data"])
        send_donation_review(phone_number, session)
    else:
        # If a location is sent unexpectedly, you might want to ignore it or handle it.
        print(f"[LOCATION] Received location from {phone_number} in an unexpected state: {session.current_state}")


def _get_message(key: str, lang: str, **kwargs) -> str:
    """Helper to get a message string in the correct language."""
    message = MESSAGES.get(lang, MESSAGES["en"]).get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message


def handle_text_message(phone_number: str, msg_text_raw: str, session) -> None:
    # Debug: print state before any processing
    print("=" * 60)
    print("[TEXT] ENTERED handle_text_message")
    print(f"[TEXT] PHONE: {phone_number}")
    print(f"[TEXT] STATE: {session.current_state}")
    print(f"[TEXT] INPUT: {repr(msg_text_raw)}")

    cmd = normalize_command(msg_text_raw)
    print(f"[TEXT] CMD: {repr(cmd)}")

    # If the session is cleared or new, ask for language.
    # Any text input will trigger this.
    if session.current_state == "MENU":
        SessionService.clear(session)
        SessionService.update_state(session, "LANGUAGE_SELECT")
        whatsapp_service.send_interactive_buttons(
            phone_number,
            MESSAGES["en"]["choose_language"] + "\n\n" + MESSAGES["ta"]["choose_language"],
            [
                {"type": "reply", "reply": {"id": "lang_en", "title": "English"}},
                {"type": "reply", "reply": {"id": "lang_ta", "title": "தமிழ் (Tamil)"}},
            ],
        )
        return

    # If in language select, re-prompt the user.
    # This handles cases where the user types text instead of clicking a button.
    if session.current_state == "LANGUAGE_SELECT":
        # Re-send the original language selection prompt with buttons.
        # Sending an interactive message with an empty button list is invalid.
        whatsapp_service.send_interactive_buttons(
            phone_number,
            MESSAGES["en"]["choose_language"] + "\n\n" + MESSAGES["ta"]["choose_language"],
            [
                {"type": "reply", "reply": {"id": "lang_en", "title": "English"}},
                {"type": "reply", "reply": {"id": "lang_ta", "title": "தமிழ் (Tamil)"}},
            ],
        )
        return

    lang = getattr(session, 'language', 'en')
    if cmd == _get_message("cancel_button", lang).lower() or cmd == "cancel":
        SessionService.clear(session)
        # Restart the flow by asking for language again
        handle_text_message(phone_number, "restart", session)
        return

    if cmd == _get_message("pay_now_button", lang).lower() or cmd == "pay_now":
        donation_id = (session.session_data or {}).get("donation_id")
        if not donation_id:
            whatsapp_service.send_text_message(phone_number, _get_message("unrecognized_command", lang))
            SessionService.clear(session)
            return
        donation = Donation.objects.filter(id=donation_id).first()
        if not donation:
            whatsapp_service.send_text_message(phone_number, _get_message("unrecognized_command", lang))
            SessionService.clear(session)
            return
        send_pay_now_cta(phone_number, donation.reference_number, donation.amount, lang)
        SessionService.clear(session)
        return

    # Get the current state and data from the session for state-specific logic
    state = session.current_state
    data = session.session_data or {}

    # ===================== FOOD =====================
    if state == "FOOD_FORM_QUANTITY":
        print(f"[STATE] MATCH! FOOD_FORM_QUANTITY")
        print(f"[STATE] MATCH! state == FOOD_FORM_QUANTITY")
        print("=" * 50)
        print("[QTY] ENTERED FOOD_FORM_QUANTITY HANDLER!")
        print(f"[QTY] state: {state}")
        print(f"[QTY] input: {repr(msg_text_raw)}")
        print(f"[QTY] stripped: {repr((msg_text_raw or '').strip())}")

        qty_str = (msg_text_raw or "").strip()
        errors = []

        # Validation: Required
        if not qty_str:
            errors.append("• Quantity is required.")

        # Validation: Whole number only
        try:
            qty = int(qty_str)
        except ValueError:
            errors.append("• Quantity must be a whole number.")

        if not errors:
            # Validation: Greater than 0
            if qty <= 0:
                errors.append("• Quantity must be greater than 0.")
            # Validation: Maximum 50,000
            elif qty > 50000:
                errors.append("• Maximum allowed quantity is 50,000.")

        if errors:
            print(f"[QTY] VALIDATION ERRORS: {errors}")
            error_message = f"❌ {_get_message('form_error_header', lang)}\n\n" + "\n".join(errors)
            whatsapp_service.send_text_message(phone_number, error_message)
            print(f"[QTY] FAILED, state stays: FOOD_FORM_QUANTITY")
            return

        # Quantity is valid
        print(f"[QTY] parsed: {qty}")
        data["quantity"] = qty
        food_item = data.get("selected_food_item") or {}
        unit_price = safe_decimal(food_item.get("price"), 0)
        base_total = unit_price * qty
        data["base_total"] = str(base_total)
        data["amount_total"] = str(base_total)
        session.session_data = data
        session.save(update_fields=["session_data"])

        # All donor details collected, now ask for packages
        # This block transitions any lingering sessions to the new flow.
        # Start the sequential donor detail collection
        SessionService.update_state(session, "FOOD_FORM_FULL_NAME")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_full_name", lang))
        return

    if state == "FOOD_FORM_FULL_NAME":
        from whatsapp_app.services.validation_service import validate_name
        errors = validate_name(msg_text_raw)
        if errors: # pragma: no cover
            send_validation_errors(phone_number, errors, lang)
            return
        data["full_name"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_EMAIL")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_email", lang))
        return

    if state == "FOOD_FORM_EMAIL":
        from whatsapp_app.services.validation_service import validate_email
        errors = validate_email(msg_text_raw)
        if errors:
            send_validation_errors(phone_number, errors, lang)
            return
        data["email"] = msg_text_raw.strip().lower()
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_MOBILE")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_mobile", lang))
        return

    if state == "FOOD_FORM_MOBILE":
        from whatsapp_app.services.validation_service import validate_mobile
        errors = validate_mobile(msg_text_raw, lang)
        if errors:
            send_validation_errors(phone_number, errors, lang)
            return
        data["mobile_number"] = extract_digits(msg_text_raw)
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_INSTAGRAM")
        whatsapp_service.send_interactive_buttons(
            phone_number,
            _get_message("instagram_prompt_body", lang),
            [
                {"type": "reply", "reply": {"id": "instagram_enter", "title": _get_message("enter_button", lang)}},
                {"type": "reply", "reply": {"id": "instagram_skip", "title": _get_message("skip_button", lang)}},
            ],
            header_text=_get_message("ask_instagram", lang),
        )
        return

    if state == "FOOD_FORM_INSTAGRAM":
        # This state is now for processing the text input *after* user chose "Enter"
        data["instagram_id"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "AWAITING_LOCATION")
        send_location_request(phone_number, lang)
        return

    if state == "FOOD_PACKAGES_SELECT":
        # This block now handles both text-based package selection (e.g., "1,3") and skipping ("skip").
        package_ids_typed = parse_package_selection(msg_text_raw)

        donor = {
            "full_name": data.get("full_name", ""),
            "email": data.get("email", ""),
            "mobile_number": data.get("mobile_number", ""),
            "instagram_id": data.get("instagram_id", ""),
        }

        food_item = data.get("selected_food_item") or {}
        qty = int(data.get("quantity") or 1)
        base_total = safe_decimal(data.get("base_total") or "0", 0)

        packages_qs = list(
            Package.objects.filter(is_active=True, category__in=["FOOD", "ALL"]).order_by("display_order", "name")
        )

        selected_pkg_objs = []
        for n in package_ids_typed:
            idx = n - 1
            if 0 <= idx < len(packages_qs):
                selected_pkg_objs.append(packages_qs[idx])

        selected_pkg_ids = [p.id for p in selected_pkg_objs]
        package_total = sum((p.price for p in selected_pkg_objs), Decimal("0"))
        total_amount = base_total + package_total

        session.session_data = {
            **data,
            "selected_package_ids": selected_pkg_ids,
            "package_total": str(package_total),
            "grand_total": str(total_amount),
        }
        session.save(update_fields=["session_data"])

        donation = DonationService.create_food_donation(
            phone_number=phone_number,
            donor_name=donor["full_name"],
            donor_email=donor["email"],
            donor_mobile=donor["mobile_number"],
            donor_instagram=donor["instagram_id"],
            selected_food_item=food_item,
            quantity=qty,
            selected_package_ids=selected_pkg_ids,
            package_total=package_total,
            base_total=base_total,
        )

        session.session_data = {**(session.session_data or {}), "donation_id": donation.id}
        session.save(update_fields=["session_data"])
        SessionService.update_state(session, "FOOD_REVIEW")

        # --- Build and send the Donation Summary ---
        package_names = [p.name for p in selected_pkg_objs]
        package_summary = f"\n🎁 Packages: {', '.join(package_names)}" if package_names else ""

        review = (
            f"{_get_message('donation_review_header', lang)}\n\n"
            f"{_get_message('item_label', lang)}: {food_item.get('name','')}\n"
            f"{_get_message('quantity_label', lang)}: {qty}\n"
            f"{_get_message('food_total_label', lang)}: ₹{base_total:,.0f}"
            f"{package_summary}\n"
            f"{_get_message('grand_total_label', lang)}: ₹{total_amount:,.0f}\n\n"
            f"{_get_message('donor_name_label', lang)} {donor['full_name']}\n"
            f"{_get_message('donor_email_label', lang)} {donor['email']}\n"
            f"{_get_message('donor_mobile_label', lang)} {donor['mobile_number']}"
        )

        whatsapp_service.send_text_message(phone_number, review)

        # --- Send the "Pay Now" CTA URL button ---
        body_text = f"Your donation of ₹{total_amount:,.0f} is ready. Click below to complete the payment."

        # Generate dynamic payment URL
        payment_init_result = easebuzz_service.initiate_payment(donation)
        if not payment_init_result.get("success"):
            error_msg = payment_init_result.get("error", "Could not initiate payment.")
            whatsapp_service.send_text_message(phone_number, f"❌ We're sorry, but there was an issue generating the payment link: {error_msg}")
            return

        payment_url = payment_init_result.get("payment_url", settings.THAAGAM_FOUNDATION['WEBSITE'])

        whatsapp_service.send_interactive_cta_url(
            phone_number,
            _get_message("payment_cta_body", lang, amount=total_amount),
            _get_message("pay_now_button", lang),
            payment_url,
            header_text=_get_message("payment_cta_header", lang),
        )
        whatsapp_service.send_text_message(phone_number, _get_message("conversation_ended", lang))
        SessionService.clear(session)

    print(f"[STATE] CHECK: {repr(state)} == EDU_STUDENT_SELECTED_AMOUNT")

    # ===================== EDUCATION =====================
    if state == "EDU_STUDENT_SELECTED_AMOUNT":
        try:
            amt = safe_decimal(msg_text_raw, 0)
            if amt < 100:
                whatsapp_service.send_text_message(phone_number, _get_message("invalid_amount_minimum", lang, amount=100))
                return
            data["donation_amount"] = str(amt)
            SessionService.set_data(session, "donation_amount", str(amt))

            # Start the sequential donor detail collection
            SessionService.update_state(session, "EDU_FORM_FULL_NAME")
            whatsapp_service.send_text_message(phone_number, _get_message("ask_full_name", lang))
        except (ValueError, TypeError):
            whatsapp_service.send_text_message(phone_number, _get_message("invalid_amount_format", lang))
        return

    if state == "EDU_FORM_FULL_NAME":
        from whatsapp_app.services.validation_service import validate_name
        errors = validate_name(msg_text_raw)
        if errors: # pragma: no cover
            send_validation_errors(phone_number, errors, lang)
            return
        data["full_name"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "EDU_FORM_EMAIL")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_email", lang))
        return

    if state == "EDU_FORM_EMAIL":
        from whatsapp_app.services.validation_service import validate_email
        all_errors = validate_email(msg_text_raw)
        if all_errors:
            send_validation_errors(phone_number, all_errors, lang)
            return
        data["email"] = msg_text_raw.strip().lower()
        session.session_data = data
        SessionService.update_state(session, "EDU_FORM_MOBILE")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_mobile", lang))
        return

    if state == "EDU_FORM_MOBILE":
        from whatsapp_app.services.validation_service import validate_mobile
        all_errors = validate_mobile(msg_text_raw, lang)
        if all_errors:
            send_validation_errors(phone_number, all_errors, lang)
            return
        data["mobile_number"] = extract_digits(msg_text_raw)
        session.session_data = data
        SessionService.update_state(session, "EDU_FORM_INSTAGRAM")
        whatsapp_service.send_interactive_buttons(
            phone_number,
            _get_message("instagram_prompt_body", lang),
            [
                {"type": "reply", "reply": {"id": "instagram_enter", "title": _get_message("enter_button", lang)}},
                {"type": "reply", "reply": {"id": "instagram_skip", "title": _get_message("skip_button", lang)}},
            ],
            header_text=_get_message("ask_instagram", lang),
        )
        return

    if state == "EDU_FORM_INSTAGRAM":
        # FIX: This block previously kept executing AFTER requesting the
        # location — it immediately created the donation, sent the review +
        # Pay Now CTA, and cleared the session right here, before the user
        # ever shared their location. By the time the location actually
        # arrived, the session had already been wiped, so
        # handle_location_message() saw an "unexpected state" and silently
        # did nothing (the "sorry" fallback). This now mirrors the working
        # FOOD_FORM_INSTAGRAM block exactly: save the Instagram ID, request
        # the location, and STOP. The donation + review + Pay Now are sent
        # later by send_donation_review(), once the location actually comes in.
        data["instagram_id"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "AWAITING_LOCATION")
        send_location_request(phone_number, lang)
        return

    print(f"[STATE] CHECK: {repr(state)} == MED_PATIENT_SELECTED_AMOUNT")

    # ===================== MEDICAL =====================
    if state == "MED_PATIENT_SELECTED_AMOUNT":
        try:
            amt = safe_decimal(msg_text_raw, 0)
            if amt < 100:
                whatsapp_service.send_text_message(phone_number, _get_message("invalid_amount_minimum", lang, amount=100))
                return
            data["donation_amount"] = str(amt)
            SessionService.set_data(session, "donation_amount", str(amt))

            # Start the sequential donor detail collection
            SessionService.update_state(session, "MED_FORM_FULL_NAME")
            whatsapp_service.send_text_message(phone_number, _get_message("ask_full_name", lang))
        except (ValueError, TypeError):
            whatsapp_service.send_text_message(phone_number, _get_message("invalid_amount_format", lang))
        return

    if state == "MED_FORM_FULL_NAME":
        from whatsapp_app.services.validation_service import validate_name
        errors = validate_name(msg_text_raw)
        if errors: # pragma: no cover
            send_validation_errors(phone_number, errors, lang)
            return
        data["full_name"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "MED_FORM_EMAIL")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_email", lang))
        return

    if state == "MED_FORM_EMAIL":
        from whatsapp_app.services.validation_service import validate_email
        all_errors = validate_email(msg_text_raw)
        if all_errors:
            send_validation_errors(phone_number, all_errors, lang)
            return
        data["email"] = msg_text_raw.strip().lower()
        session.session_data = data
        SessionService.update_state(session, "MED_FORM_MOBILE")
        whatsapp_service.send_text_message(phone_number, _get_message("ask_mobile", lang))
        return

    if state == "MED_FORM_MOBILE":
        from whatsapp_app.services.validation_service import validate_mobile
        all_errors = validate_mobile(msg_text_raw, lang)
        if all_errors:
            send_validation_errors(phone_number, all_errors, lang)
            return
        data["mobile_number"] = extract_digits(msg_text_raw)
        session.session_data = data
        SessionService.update_state(session, "MED_FORM_INSTAGRAM")
        whatsapp_service.send_interactive_buttons(
            phone_number,
            _get_message("instagram_prompt_body", lang),
            [
                {"type": "reply", "reply": {"id": "instagram_enter", "title": _get_message("enter_button", lang)}},
                {"type": "reply", "reply": {"id": "instagram_skip", "title": _get_message("skip_button", lang)}},
            ],
            header_text=_get_message("ask_instagram", lang),
        )
        return

    if state == "MED_FORM_INSTAGRAM":
        # FIX: same issue and same fix as EDU_FORM_INSTAGRAM above — stop
        # right after requesting the location instead of immediately
        # creating the donation and clearing the session. send_donation_review()
        # takes over once the location is actually received.
        data["instagram_id"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "AWAITING_LOCATION")
        send_location_request(phone_number, lang)
        return

    # Default handler for unrecognized text messages
    # If the input doesn't match any state, reset the conversation.
    # This prevents the user from getting stuck.
    SessionService.clear(session)
    handle_text_message(phone_number, "restart", session)


def handle_interactive_selection(phone_number: str, selection_id: str, session) -> None:
    from whatsapp_app.services.validation_service import (
        send_validation_errors,
    )

    print("=" * 60)
    print("[INTERACTIVE] ENTERED handle_interactive_selection")
    print(f"[INTERACTIVE] PHONE: {phone_number}")
    print(f"[INTERACTIVE] STATE: {session.current_state}")
    print(f"[INTERACTIVE] SELECTION: {repr(selection_id)}")

    sid = (selection_id or "").strip().lower()
    lang = session.language or "en"

    if sid.startswith("lang_"):
        lang_code = sid.split("_")[1]
        SessionService.set_language(session, lang_code)
        SessionService.update_state(session, "MAIN_MENU")
        send_menu(phone_number, lang_code)
        return

    if sid == "contact" or sid == _get_message("contact_button", lang).lower():
        send_contact(phone_number, lang)
        return

    if sid == "location" or sid == _get_message("location_button", lang).lower():
        send_location(phone_number, lang)
        return

    if sid in {"menu", "main_menu"}:
        SessionService.clear(session)
        # Restart flow by asking for language
        handle_text_message(phone_number, "restart", session)
        return

    if sid == "pay_now" or sid == _get_message("pay_now_button", lang).lower():
        donation_id = (session.session_data or {}).get("donation_id")
        if not donation_id:
            whatsapp_service.send_text_message(phone_number, _get_message("unrecognized_command", lang))
            SessionService.clear(session)
            return
        donation = Donation.objects.filter(id=donation_id).first()
        if not donation:
            whatsapp_service.send_text_message(phone_number, _get_message("unrecognized_command", lang))
            SessionService.clear(session)
            return
        send_pay_now_cta(phone_number, donation.reference_number, donation.amount, lang)
        SessionService.clear(session)
        return

    if sid == "cancel" or sid == _get_message("cancel_button", lang).lower():
        SessionService.clear(session)
        # Restart flow by asking for language
        handle_text_message(phone_number, "restart", session)
        return

    if sid == "donate" or sid == _get_message("donate_button", lang).lower():
        SessionService.update_state(session, "CATEGORY_SELECT")
        send_donate_category_menu(phone_number, lang)
        return

    if sid == "donate_food":
        SessionService.update_state(session, "FOOD_ITEM_SELECT")
        SessionService.set_data(session, "flow_category", "FOOD")
        session.session_data = session.session_data or {}
        session.save(update_fields=["session_data", "current_state"])
        send_food_items_list(phone_number, lang)
        return

    if sid.startswith("food_"):
        item_id = int(sid.replace("food_", ""))
        item = FoodItem.objects.filter(id=item_id, is_active=True).first()
        if not item:
            send_food_items_list(phone_number, lang)
            return
        data = session.session_data or {}
        data["selected_food_item"] = {"id": item.id, "name": item.name, "price": str(item.price_per_unit), "unit": item.unit_label}
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_QUANTITY")
        print(f"[SELECT] Set FOOD_FORM_QUANTITY, selected_food_item: {data.get('selected_food_item')}")
        whatsapp_service.send_text_message(
            phone_number,
            f"✅ {_get_message('item_selected', lang, item_name=item.name)}\n{_get_message('item_price', lang, price=item.price_per_unit, unit=item.unit_label)}\n\n{_get_message('ask_quantity', lang)}",
        )
        return

    if sid == "donate_education":
        SessionService.update_state(session, "EDU_STUDENT_SELECT")
        # FIX: was "EDUCATION" — must be "EDU" to match what
        # send_donation_review() checks for (flow_prefix == "EDUCATION").
        # The old mismatched value meant a successfully-shared location
        # would still fail to produce a donation/review/Pay Now message.
        SessionService.set_data(session, "flow_category", "EDUCATION")
        send_student_list(phone_number, lang)
        return

    if sid.startswith("student_"):
        student_id = int(sid.replace("student_", ""))
        student = Student.objects.filter(id=student_id, is_active=True).first()
        if not student:
            send_student_list(phone_number, lang)
            return
        data = session.session_data or {}
        data["selected_student"] = {"id": student.id, "name": student.name}
        session.session_data = data
        SessionService.update_state(session, "EDU_STUDENT_SELECTED_AMOUNT")
        print(f"[SELECT] Set EDU_STUDENT_SELECTED_AMOUNT, selected_student: {data.get('selected_student')}")
        whatsapp_service.send_text_message(phone_number, f"🎓 {student.name}\n\n{_get_message('ask_donation_amount', lang, amount=100)}")
        return

    if sid == "donate_medical":
        SessionService.update_state(session, "MED_PATIENT_SELECT")
        # FIX: was "MEDICAL" — must be "MED" to match what
        # send_donation_review() checks for (flow_prefix == "MEDICAL").
        SessionService.set_data(session, "flow_category", "MEDICAL")
        send_patient_list(phone_number, lang)
        return

    if sid.startswith("patient_"):
        patient_id = int(sid.replace("patient_", ""))
        patient = Patient.objects.filter(id=patient_id, is_active=True).first()
        if not patient:
            send_patient_list(phone_number, lang)
            return
        data = session.session_data or {}
        data["selected_patient"] = {"id": patient.id, "name": patient.name}
        session.session_data = data
        SessionService.update_state(session, "MED_PATIENT_SELECTED_AMOUNT")
        print(f"[SELECT] Set MED_PATIENT_SELECTED_AMOUNT, selected_patient: {data.get('selected_patient')}")
        remaining = max(patient.goal_amount - patient.raised_amount, 0)
        whatsapp_service.send_text_message(
            phone_number,
            f"🏥 {patient.name}\n{_get_message('hospital_label', lang)}: {patient.hospital}\n{_get_message('remaining_needed_label', lang)}: ₹{remaining:,.0f}\n\n{_get_message('ask_donation_amount', lang, amount=100)}",
        )
        return

    if sid == "instagram_enter":
        # User wants to enter their ID. Change state to wait for text input.
        # With the _state_category() fix above, current_flow_prefix is now
        # "FOOD" / "EDU" / "MED" — matching the real state-name prefixes —
        # so this correctly rebuilds "EDU_FORM_INSTAGRAM" / "MED_FORM_INSTAGRAM"
        # instead of the broken "EDUCATION_FORM_INSTAGRAM" / "MEDICAL_FORM_INSTAGRAM".
        current_flow_prefix = _state_category(session.current_state)
        if current_flow_prefix:
            SessionService.update_state(session, f"{current_flow_prefix}_FORM_INSTAGRAM")
            whatsapp_service.send_text_message(phone_number, _get_message("ask_instagram", lang))
        return

    if sid == "instagram_skip":
        # User wants to skip. Set ID to empty and move to the next step.
        session.session_data["instagram_id"] = ""
        _move_to_next_step_after_instagram(phone_number, session)
        return

    if sid.startswith("pkg_"):
        print("Reached package handler")
        state = session.current_state
        if state != "FOOD_PACKAGES_SELECT":
            # If we are not in the package selection state, ignore this.
            return

        # This block handles interactive list selections for packages.
        data = session.session_data or {}
        try:
            pkg_id = int(sid.replace("pkg_", ""))
            package = Package.objects.get(id=pkg_id, is_active=True)
            print("Package loaded")

            # --- Create Donation and Send Summary ---
            donor = {
                "full_name": data.get("full_name", ""), "email": data.get("email", ""),
                "mobile_number": data.get("mobile_number", ""), "instagram_id": data.get("instagram_id", ""),
            }
            food_item = data.get("selected_food_item") or {}
            qty = int(data.get("quantity") or 1)
            base_total = safe_decimal(data.get("base_total") or "0", 0)

            # For a single selection, the package total is just this package's price.
            package_total = package.price
            total_amount = base_total + package_total

            donation = DonationService.create_food_donation(
                phone_number=phone_number, donor_name=donor["full_name"], donor_email=donor["email"],
                donor_mobile=donor["mobile_number"], donor_instagram=donor["instagram_id"],
                selected_food_item=food_item, quantity=qty, selected_package_ids=[package.id],
                package_total=package_total, base_total=base_total,
            )

            data["donation_id"] = donation.id
            session.session_data = data
            SessionService.update_state(session, "FOOD_REVIEW")
            print("Session and state updated for review.")

            # --- Build and send the Donation Summary ---
            review = (
                f"{_get_message('donation_review_header', lang)}\n\n"
                f"{_get_message('item_label', lang)}: {food_item.get('name','')}\n"
                f"{_get_message('quantity_label', lang)}: {qty}\n"
                f"{_get_message('food_total_label', lang)}: ₹{base_total:,.0f}\n"
                f"{_get_message('packages_label', lang)}: {package.name}\n"
                f"{_get_message('grand_total_label', lang)}: ₹{total_amount:,.0f}\n\n"
                f"{_get_message('donor_name_label', lang)} {donor['full_name']}\n"
                f"{_get_message('donor_email_label', lang)} {donor['email']}\n"
                f"{_get_message('donor_mobile_label', lang)} {donor['mobile_number']}"
            )
            whatsapp_service.send_text_message(phone_number, review)

            # --- Send the "Pay Now" CTA URL button ---
            send_pay_now_cta(phone_number, donation.reference_number, total_amount, lang)
            whatsapp_service.send_text_message(phone_number, _get_message("conversation_ended", lang))
            SessionService.clear(session)

        except (ValueError, Package.DoesNotExist):
            whatsapp_service.send_text_message(phone_number, _get_message("invalid_selection", lang))
        return


def send_donation_review(phone_number: str, session) -> None:
    """
    Builds and sends the final donation review summary based on the session data,
    then triggers the payment CTA. This function is flow-agnostic.
    """
    lang = session.language
    data = session.session_data or {}
    flow_prefix = data.get("flow_category")

    # --- Create the Donation Record ---
    # This part is now centralized here.
    donor_details = {
        "phone_number": phone_number,
        "donor_name": data.get("full_name", ""),
        "donor_email": data.get("email", ""),
        "donor_mobile": data.get("mobile_number", ""),
        "donor_instagram": data.get("instagram_id", ""),
    }

    donation = None
    review_lines = [f"{_get_message('donation_review_header', lang)}\n"]

    if flow_prefix == "FOOD":
        food_item = data.get("selected_food_item", {})
        qty = int(data.get("quantity", 1))
        base_total = safe_decimal(data.get("base_total", "0"))
        package_total = safe_decimal(data.get("package_total", "0"))
        selected_pkg_ids = data.get("selected_package_ids", [])

        donation = DonationService.create_food_donation(
            **donor_details,
            selected_food_item=food_item,
            quantity=qty,
            selected_package_ids=selected_pkg_ids,
            package_total=package_total,
            base_total=base_total,
        )
        review_lines.append(f"{_get_message('item_label', lang)}: {food_item.get('name', '')}")
        review_lines.append(f"{_get_message('quantity_label', lang)}: {qty}")
        review_lines.append(f"{_get_message('grand_total_label', lang)}: ₹{donation.amount:,.0f}")

    elif flow_prefix == "EDUCATION":
        student = data.get("selected_student", {})
        amount = safe_decimal(data.get("donation_amount", "0"))
        donation = DonationService.create_education_donation(**donor_details, selected_student=student, amount=amount)
        review_lines.append(f"{_get_message('student_label', lang)}: {student.get('name', '')}")
        review_lines.append(f"{_get_message('amount_label', lang)}: ₹{donation.amount:,.0f}")

    elif flow_prefix == "MEDICAL":
        patient = data.get("selected_patient", {})
        amount = safe_decimal(data.get("donation_amount", "0"))
        donation = DonationService.create_medical_donation(**donor_details, selected_patient=patient, amount=amount)
        review_lines.append(f"{_get_message('patient_label', lang)}: {patient.get('name', '')}")
        review_lines.append(f"{_get_message('amount_label', lang)}: ₹{donation.amount:,.0f}")

    if not donation:
        whatsapp_service.send_text_message(phone_number, _get_message("unrecognized_command", lang))
        return

    # --- Send the Review and Payment CTA ---
    review_lines.append(f"\n{_get_message('donor_name_label', lang)} {donor_details['donor_name']}")
    review_lines.append(f"{_get_message('donor_email_label', lang)} {donor_details['donor_email']}")
    review_lines.append(f"{_get_message('donor_mobile_label', lang)} {donor_details['donor_mobile']}")

    review_message = "\n".join(review_lines)
    whatsapp_service.send_text_message(phone_number, review_message)

    send_pay_now_cta(phone_number, donation.reference_number, donation.amount, lang)
    whatsapp_service.send_text_message(phone_number, _get_message("conversation_ended", lang))
    SessionService.clear(session)


def _move_to_next_step_after_instagram(phone_number: str, session) -> None:
    """Helper to transition to the correct next step after Instagram ID handling."""
    lang = session.language

    # For all flows, the next step is now to request the user's location.
    SessionService.update_state(session, "AWAITING_LOCATION")
    send_location_request(phone_number, lang)