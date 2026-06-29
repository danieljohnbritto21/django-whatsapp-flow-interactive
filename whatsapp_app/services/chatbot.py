from __future__ import annotations

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
    if state.startswith("FOOD_"):
        return "FOOD"
    if state.startswith("EDU_"):
        return "EDUCATION"
    if state.startswith("MED_"):
        return "MEDICAL"
    return None


def handle_text_message(phone_number: str, msg_text_raw: str, session) -> None:
    # Debug: print state before any processing
    print("=" * 60)
    print("[TEXT] ENTERED handle_text_message")
    print(f"[TEXT] PHONE: {phone_number}")
    print(f"[TEXT] STATE: {session.current_state}")
    print(f"[TEXT] INPUT: {repr(msg_text_raw)}")

    cmd = normalize_command(msg_text_raw)
    print(f"[TEXT] CMD: {repr(cmd)}")

    if cmd in {"hi", "hello", "start", "hey", "menu"}:
        SessionService.clear(session)
        send_menu(phone_number)
        return

    if cmd == "contact":
        SessionService.update_state(session, "MENU")
        send_contact(phone_number)
        return

    if cmd == "location":
        SessionService.update_state(session, "MENU")
        send_location(phone_number)
        return

    if cmd == "cancel":
        SessionService.clear(session)
        send_menu(phone_number)
        return

    if cmd == "pay_now":
        donation_id = (session.session_data or {}).get("donation_id")
        if not donation_id:
            whatsapp_service.send_text_message(phone_number, "No active payment found. Please start again: type *Hi*.")
            SessionService.clear(session)
            return
        donation = Donation.objects.filter(id=donation_id).first()
        if not donation:
            whatsapp_service.send_text_message(phone_number, "Payment record not found. Please start again: type *Hi*.")
            SessionService.clear(session)
            return
        send_pay_now_cta(phone_number, donation.reference_number, donation.amount)
        SessionService.clear(session)
        return

    state = session.current_state
    data = session.session_data or {}

    print(f"[STATE] CHECK: {repr(state)}")

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
            error_message = "❌ Please correct the following:\n\n" + "\n".join(errors)
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
        whatsapp_service.send_text_message(phone_number, "👤 Please enter your *Full Name*.")
        return

    if state == "FOOD_FORM_FULL_NAME":
        from whatsapp_app.services.validation_service import validate_name
        errors = validate_name(msg_text_raw)
        if errors: # pragma: no cover
            send_validation_errors(phone_number, errors)
            return
        data["full_name"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_EMAIL")
        whatsapp_service.send_text_message(phone_number, "📧 Please enter your *Email Address*.")
        return

    if state == "FOOD_FORM_EMAIL":
        from whatsapp_app.services.validation_service import validate_email
        errors = validate_email(msg_text_raw)
        if errors:
            send_validation_errors(phone_number, errors)
            return
        data["email"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_MOBILE")
        whatsapp_service.send_text_message(phone_number, "📱 Please enter your *Mobile Number*.")
        return

    if state == "FOOD_FORM_MOBILE":
        from whatsapp_app.services.validation_service import validate_mobile
        errors = validate_mobile(msg_text_raw)
        if errors:
            send_validation_errors(phone_number, errors)
            return
        data["mobile_number"] = extract_digits(msg_text_raw)
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_INSTAGRAM")
        whatsapp_service.send_text_message(phone_number, "📸 Please enter your *Instagram ID*.\n(Type \"Skip\" if not applicable)")
        return

    if state == "FOOD_FORM_INSTAGRAM":
        data["instagram_id"] = "" if cmd == "skip" else msg_text_raw.strip()
        session.session_data = data
        session.save(update_fields=["session_data"])

        # All donor details collected, now ask for packages
        SessionService.update_state(session, "FOOD_PACKAGES_SELECT")
        send_optional_packages(phone_number)
        whatsapp_service.send_text_message(phone_number, "Type selection like `1,3` or `skip`.")
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
            "📋 *Donation Review*\n\n"
            f"🍲 Item: {food_item.get('name','')}\n"
            f"📦 Quantity: {qty}\n"
            f"💰 Food Total: ₹{base_total:,.0f}"
            f"{package_summary}\n"
            f"🎯 Grand Total: ₹{total_amount:,.0f}\n\n"
            f"👤 {donor['full_name']}\n"
            f"✉️ {donor['email']}\n"
            f"📱 {donor['mobile_number']}"
        )

        whatsapp_service.send_text_message(phone_number, review)

        # --- Send the "Pay Now" CTA URL button ---
        body_text = f"Your donation of ₹{total_amount:,.0f} is ready. Click below to complete the payment."
        whatsapp_service.send_interactive_cta_url(
            phone_number, body_text, "Pay Now", "https://thaagam.org/referral/qpay/HBSGF/", header_text="💳 Complete Your Payment"
        )
        return

    print(f"[STATE] CHECK: {repr(state)} == EDU_STUDENT_SELECTED_AMOUNT")

    # ===================== EDUCATION =====================
    if state == "EDU_STUDENT_SELECTED_AMOUNT":
        try:
            amt = safe_decimal(msg_text_raw, 0)
            if amt < 100:
                whatsapp_service.send_text_message(phone_number, "❌ Invalid amount. Minimum ₹100.")
                return
            data["donation_amount"] = str(amt)
            SessionService.set_data(session, "donation_amount", str(amt))

            # Start the sequential donor detail collection
            SessionService.update_state(session, "EDU_FORM_FULL_NAME")
            whatsapp_service.send_text_message(phone_number, "👤 Please enter your *Full Name*.")
        except (ValueError, TypeError):
            whatsapp_service.send_text_message(phone_number, "❌ Please enter a valid amount (e.g., 500).")
        return
    
    if state == "EDU_FORM_FULL_NAME":
        from whatsapp_app.services.validation_service import validate_name
        errors = validate_name(msg_text_raw)
        if errors: # pragma: no cover
            send_validation_errors(phone_number, errors)
            return
        data["full_name"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "EDU_FORM_EMAIL")
        whatsapp_service.send_text_message(phone_number, "📧 Please enter your *Email Address*.")
        return

    if state == "EDU_FORM_EMAIL":
        from whatsapp_app.services.validation_service import validate_email
        all_errors = validate_email(msg_text_raw)
        if all_errors:
            send_validation_errors(phone_number, all_errors)
            return
        data["email"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "EDU_FORM_MOBILE")
        whatsapp_service.send_text_message(phone_number, "📱 Please enter your *Mobile Number*.")
        return

    if state == "EDU_FORM_MOBILE":
        from whatsapp_app.services.validation_service import validate_mobile
        all_errors = validate_mobile(msg_text_raw)
        if all_errors:
            send_validation_errors(phone_number, all_errors)
            return
        data["mobile_number"] = extract_digits(msg_text_raw)
        session.session_data = data
        SessionService.update_state(session, "EDU_FORM_INSTAGRAM")
        whatsapp_service.send_text_message(phone_number, "📸 Please enter your *Instagram ID*.\n(Type \"Skip\" if not applicable)")
        return

    if state == "EDU_FORM_INSTAGRAM":
        data["instagram_id"] = "" if cmd == "skip" else msg_text_raw.strip()
        session.session_data = data
        session.save(update_fields=["session_data"])

        # All details collected, create donation and show summary
        # Create donation and proceed to review
        selected_student = data.get("selected_student") or {}
        donation_amount = safe_decimal(data.get("donation_amount"), 0)

        donation = DonationService.create_education_donation(
            phone_number=phone_number,
            donor_name=data.get("full_name", ""),
            donor_email=data.get("email", ""),
            donor_mobile=data.get("mobile_number", ""),
            donor_instagram=data.get("instagram_id", ""),
            selected_student=selected_student,
            amount=donation_amount,
        )

        session.session_data["donation_id"] = donation.id
        session.save(update_fields=["session_data"])
        SessionService.update_state(session, "EDU_REVIEW")

        # --- Build and send the Donation Summary ---
        review = (
            "📋 *Donation Review*\n\n"
            f"🎓 Student: {selected_student.get('name','')}\n"
            f"💰 Amount: ₹{donation_amount:,.0f}\n\n"
            f"👤 {data.get('full_name','')}\n"
            f"✉️ {data.get('email','')}\n"
            f"📱 {data.get('mobile_number','')}"
        )
        whatsapp_service.send_text_message(phone_number, review)

        # --- Send the "Pay Now" CTA URL button ---
        body_text = f"Your donation of ₹{donation_amount:,.0f} is ready. Click below to complete the payment."
        whatsapp_service.send_interactive_cta_url(
            phone_number,
            body_text,
            "Pay Now",
            "https://thaagam.org/referral/qpay/HBSGF/",
            header_text="💳 Complete Your Payment",
        )
        return


    print(f"[STATE] CHECK: {repr(state)} == MED_PATIENT_SELECTED_AMOUNT")

    # ===================== MEDICAL =====================
    if state == "MED_PATIENT_SELECTED_AMOUNT":
        try:
            amt = safe_decimal(msg_text_raw, 0)
            if amt < 100:
                whatsapp_service.send_text_message(phone_number, "❌ Invalid amount. Minimum ₹100.")
                return
            data["donation_amount"] = str(amt)
            SessionService.set_data(session, "donation_amount", str(amt))

            # Start the sequential donor detail collection
            SessionService.update_state(session, "MED_FORM_FULL_NAME")
            whatsapp_service.send_text_message(phone_number, "👤 Please enter your *Full Name*.")
        except (ValueError, TypeError):
            whatsapp_service.send_text_message(phone_number, "❌ Please enter a valid amount (e.g., 500).")
        return
    
    if state == "MED_FORM_FULL_NAME":
        from whatsapp_app.services.validation_service import validate_name
        errors = validate_name(msg_text_raw)
        if errors: # pragma: no cover
            send_validation_errors(phone_number, errors)
            return
        data["full_name"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "MED_FORM_EMAIL")
        whatsapp_service.send_text_message(phone_number, "📧 Please enter your *Email Address*.")
        return

    if state == "MED_FORM_EMAIL":
        from whatsapp_app.services.validation_service import validate_email
        all_errors = validate_email(msg_text_raw)
        if all_errors:
            send_validation_errors(phone_number, all_errors)
            return
        data["email"] = msg_text_raw.strip()
        session.session_data = data
        SessionService.update_state(session, "MED_FORM_MOBILE")
        whatsapp_service.send_text_message(phone_number, "📱 Please enter your *Mobile Number*.")
        return

    if state == "MED_FORM_MOBILE":
        from whatsapp_app.services.validation_service import validate_mobile
        all_errors = validate_mobile(msg_text_raw)
        if all_errors:
            send_validation_errors(phone_number, all_errors)
            return
        data["mobile_number"] = extract_digits(msg_text_raw)
        session.session_data = data
        SessionService.update_state(session, "MED_FORM_INSTAGRAM")
        whatsapp_service.send_text_message(phone_number, "📸 Please enter your *Instagram ID*.\n(Type \"Skip\" if not applicable)")
        return

    if state == "MED_FORM_INSTAGRAM":
        data["instagram_id"] = "" if cmd == "skip" else msg_text_raw.strip()
        session.session_data = data
        session.save(update_fields=["session_data"])

        # All details collected, create donation and show summary
        # Create donation and proceed to review
        selected_patient = data.get("selected_patient") or {}
        donation_amount = safe_decimal(data.get("donation_amount"), 0)

        donation = DonationService.create_medical_donation(
            phone_number=phone_number,
            donor_name=data.get("full_name", ""),
            donor_email=data.get("email", ""),
            donor_mobile=data.get("mobile_number", ""),
            donor_instagram=data.get("instagram_id", ""),
            selected_patient=selected_patient,
            amount=donation_amount,
        )

        session.session_data["donation_id"] = donation.id
        session.save(update_fields=["session_data"])
        SessionService.update_state(session, "MED_REVIEW")

        # --- Build and send the Donation Summary ---
        review = (
            "📋 *Donation Review*\n\n"
            f"🏥 Patient: {selected_patient.get('name','')}\n"
            f"💰 Amount: ₹{donation_amount:,.0f}\n\n"
            f"👤 {data.get('full_name','')}\n"
            f"✉️ {data.get('email','')}\n"
            f"📱 {data.get('mobile_number','')}"
        )
        whatsapp_service.send_text_message(phone_number, review)

        # --- Send the "Pay Now" CTA URL button ---
        body_text = f"Your donation of ₹{donation_amount:,.0f} is ready. Click below to complete the payment."
        whatsapp_service.send_interactive_cta_url(
            phone_number,
            body_text,
            "Pay Now",
            "https://thaagam.org/referral/qpay/HBSGF/",
            header_text="💳 Complete Your Payment",
        )
        return


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

    if sid in {"menu", "main_menu"}:
        SessionService.clear(session)
        send_menu(phone_number)
        return

    if sid == "pay_now":
        donation_id = (session.session_data or {}).get("donation_id")
        if not donation_id:
            whatsapp_service.send_text_message(phone_number, "No active payment found. Please start again: type *Hi*.")
            SessionService.clear(session)
            return
        donation = Donation.objects.filter(id=donation_id).first()
        if not donation:
            whatsapp_service.send_text_message(phone_number, "Payment record not found. Please start again: type *Hi*.")
            SessionService.clear(session)
            return
        send_pay_now_cta(phone_number, donation.reference_number, donation.amount)
        SessionService.clear(session)
        return

    if sid == "cancel":
        SessionService.clear(session)
        send_menu(phone_number)
        return

    if sid == "donate":
        SessionService.update_state(session, "CATEGORY_SELECT")
        send_donate_category_menu(phone_number)
        return

    if sid == "donate_food":
        SessionService.update_state(session, "FOOD_ITEM_SELECT")
        session.session_data = session.session_data or {}
        session.save(update_fields=["session_data", "current_state"])
        send_food_items_list(phone_number)
        return

    if sid.startswith("food_"):
        item_id = int(sid.replace("food_", ""))
        item = FoodItem.objects.filter(id=item_id, is_active=True).first()
        if not item:
            send_food_items_list(phone_number)
            return
        data = session.session_data or {}
        data["selected_food_item"] = {"id": item.id, "name": item.name, "price": str(item.price_per_unit), "unit": item.unit_label}
        session.session_data = data
        SessionService.update_state(session, "FOOD_FORM_QUANTITY")
        print(f"[SELECT] Set FOOD_FORM_QUANTITY, selected_food_item: {data.get('selected_food_item')}")
        whatsapp_service.send_text_message(
            phone_number,
            f"✅ Selected: {item.name}\nPrice: ₹{item.price_per_unit}/{item.unit_label}\n\nEnter Quantity (1–50,000):",
        )
        return

    if sid == "donate_education":
        SessionService.update_state(session, "EDU_STUDENT_SELECT")
        send_student_list(phone_number)
        return

    if sid.startswith("student_"):
        student_id = int(sid.replace("student_", ""))
        student = Student.objects.filter(id=student_id, is_active=True).first()
        if not student:
            send_student_list(phone_number)
            return
        data = session.session_data or {}
        data["selected_student"] = {"id": student.id, "name": student.name}
        session.session_data = data
        SessionService.update_state(session, "EDU_STUDENT_SELECTED_AMOUNT")
        print(f"[SELECT] Set EDU_STUDENT_SELECTED_AMOUNT, selected_student: {data.get('selected_student')}")
        whatsapp_service.send_text_message(phone_number, f"🎓 {student.name}\n\nEnter donation amount (minimum ₹100):")
        return

    if sid == "donate_medical":
        SessionService.update_state(session, "MED_PATIENT_SELECT")
        send_patient_list(phone_number)
        return

    if sid.startswith("patient_"):
        patient_id = int(sid.replace("patient_", ""))
        patient = Patient.objects.filter(id=patient_id, is_active=True).first()
        if not patient:
            send_patient_list(phone_number)
            return
        data = session.session_data or {}
        data["selected_patient"] = {"id": patient.id, "name": patient.name}
        session.session_data = data
        SessionService.update_state(session, "MED_PATIENT_SELECTED_AMOUNT")
        print(f"[SELECT] Set MED_PATIENT_SELECTED_AMOUNT, selected_patient: {data.get('selected_patient')}")
        remaining = max(patient.goal_amount - patient.raised_amount, 0)
        whatsapp_service.send_text_message(
            phone_number,
            f"🏥 {patient.name}\nHospital: {patient.hospital}\nRemaining needed: ₹{remaining:,.0f}\n\nEnter donation amount (minimum ₹100):",
        )
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
                "📋 *Donation Review*\n\n"
                f"🍲 Item: {food_item.get('name','')}\n"
                f"📦 Quantity: {qty}\n"
                f"💰 Food Total: ₹{base_total:,.0f}\n"
                f"🎁 Package: {package.name}\n"
                f"🎯 Grand Total: ₹{total_amount:,.0f}\n\n"
                f"👤 {donor['full_name']}\n"
                f"✉️ {donor['email']}\n"
                f"📱 {donor['mobile_number']}"
            )
            whatsapp_service.send_text_message(phone_number, review)

            # --- Send the "Pay Now" CTA URL button ---
            body_text = f"Your donation of ₹{total_amount:,.0f} is ready. Click below to complete the payment."
            whatsapp_service.send_interactive_cta_url(
                phone_number, body_text, "Pay Now", "https://thaagam.org/referral/qpay/HBSGF/", header_text="💳 Complete Your Payment"
            )

        except (ValueError, Package.DoesNotExist):
            whatsapp_service.send_text_message(phone_number, "❌ Invalid package selected. Please try again.")
        return
