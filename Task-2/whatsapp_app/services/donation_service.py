from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from whatsapp_app.models import Donation, DonationItem, DonationPackage


class DonationService:
    @staticmethod
    def create_food_donation(
        *,
        phone_number: str,
        donor_name: str,
        donor_email: str,
        donor_mobile: str,
        donor_instagram: str | None,
        selected_food_item: Dict[str, Any],
        quantity: int,
        selected_package_ids: Sequence[int],
        package_total: Decimal,
        base_total: Decimal,
    ) -> Donation:
        total_amount = base_total + package_total

        donation = Donation.objects.create(
            whatsapp_phone_number=phone_number,
            category="FOOD",
            cause="FOOD",
            amount=total_amount,
            full_name=donor_name,
            mobile_number=donor_mobile,
            email=donor_email,
            instagram_id=donor_instagram or "",
            payment_status="PENDING",
        )

        DonationItem.objects.create(
            donation=donation,
            item_type="FOOD",
            item_name=selected_food_item.get("name") or "Food",
            item_id=int(selected_food_item.get("id") or 0),
            quantity=quantity,
            unit_price=Decimal(str(selected_food_item.get("price") or 0)),
            subtotal=base_total,
        )

        if selected_package_ids:
            from whatsapp_app.models import Package

            for pid in selected_package_ids:
                pkg = Package.objects.filter(id=pid, is_active=True).first()
                if not pkg:
                    continue
                DonationPackage.objects.create(
                    donation=donation,
                    package=pkg,
                    package_name=pkg.name,
                    price=pkg.price,
                )

        return donation

    @staticmethod
    def create_education_donation(
        *,
        phone_number: str,
        donor_name: str,
        donor_email: str,
        donor_mobile: str,
        donor_instagram: str | None,
        selected_student: Dict[str, Any],
        amount: Decimal,
    ) -> Donation:
        donation = Donation.objects.create(
            whatsapp_phone_number=phone_number,
            category="EDUCATION",
            cause="EDUCATION",
            amount=amount,
            full_name=donor_name,
            mobile_number=donor_mobile,
            email=donor_email,
            instagram_id=donor_instagram or "",
            payment_status="PENDING",
        )

        student_obj = None
        from whatsapp_app.models import Student

        if selected_student.get("id"):
            student_obj = Student.objects.filter(id=selected_student["id"], is_active=True).first()

        DonationItem.objects.create(
            donation=donation,
            item_type="STUDENT",
            item_name=(student_obj.name if student_obj else selected_student.get("name") or "Student"),
            item_id=int(selected_student.get("id") or 0),
            quantity=1,
            unit_price=amount,
            subtotal=amount,
        )

        if student_obj:
            donation.student = student_obj
            donation.save(update_fields=["student"])

        return donation

    @staticmethod
    def create_medical_donation(
        *,
        phone_number: str,
        donor_name: str,
        donor_email: str,
        donor_mobile: str,
        donor_instagram: str | None,
        selected_patient: Dict[str, Any],
        amount: Decimal,
    ) -> Donation:
        donation = Donation.objects.create(
            whatsapp_phone_number=phone_number,
            category="MEDICAL",
            cause="MEDICAL",
            amount=amount,
            full_name=donor_name,
            mobile_number=donor_mobile,
            email=donor_email,
            instagram_id=donor_instagram or "",
            payment_status="PENDING",
        )

        patient_obj = None
        from whatsapp_app.models import Patient

        if selected_patient.get("id"):
            patient_obj = Patient.objects.filter(id=selected_patient["id"], is_active=True).first()

        DonationItem.objects.create(
            donation=donation,
            item_type="PATIENT",
            item_name=(patient_obj.name if patient_obj else selected_patient.get("name") or "Patient"),
            item_id=int(selected_patient.get("id") or 0),
            quantity=1,
            unit_price=amount,
            subtotal=amount,
        )

        if patient_obj:
            donation.patient = patient_obj
            donation.save(update_fields=["patient"])

        return donation

