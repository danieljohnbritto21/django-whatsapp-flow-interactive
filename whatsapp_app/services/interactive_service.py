from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from whatsapp_app.messages import MESSAGES
from whatsapp_app.models import FoodItem, Package, Patient, Student
from whatsapp_app.whatsapp_service import whatsapp_service


def _get_message(key: str, lang: str, **kwargs) -> str:
    """Helper to get a message string in the correct language."""
    message = MESSAGES.get(lang, MESSAGES["en"]).get(key, key)
    if kwargs:
        return message.format(**kwargs)
    return message


def send_food_items_list(phone_number: str, lang: str = "en") -> bool:
    items = FoodItem.objects.filter(is_active=True).order_by("display_order", "name")
    rows = []
    for it in items:
        rows.append(
            {
                "id": f"food_{it.id}",
                "title": _get_message(f"food_item_{it.id}_name", lang)[:24],
                "description": _get_message(
                    f"food_item_{it.id}_desc",
                    lang,
                    price=it.price_per_unit,
                    unit=it.unit_label,
                )[:72],
            }
        )
    sections = [{"title": _get_message("food_list_header", lang), "rows": rows}]
    return bool(rows) and bool(
        whatsapp_service.send_interactive_list(
            phone_number,
            _get_message("food_list_body", lang),
            _get_message("food_list_button", lang),
            sections,
            header_text=_get_message("food_donation_header", lang),
            footer_text="❤️ Thaagam Foundation",
        )
    )


def send_student_list(phone_number: str, lang: str = "en") -> bool:
    students = Student.objects.filter(is_active=True).order_by("name")
    rows = []
    for s in students:
        rows.append(
            {
                "id": f"student_{s.id}",
                "title": _get_message(f"student_{s.id}_name", lang, default=s.name)[:24],
                "description": _get_message(
                    f"student_{s.id}_desc",
                    lang,
                    class_name=s.class_name,
                    school=s.school,
                )[:72],
            }
        )
    sections = [{"title": _get_message("student_list_header", lang), "rows": rows}]
    return bool(rows) and bool(
        whatsapp_service.send_interactive_list(
            phone_number,
            _get_message("student_list_body", lang),
            _get_message("student_list_button", lang),
            sections,
            header_text=_get_message("education_sponsorship_header", lang),
            footer_text="❤️ Thaagam Foundation",
        )
    )


def send_patient_list(phone_number: str, lang: str = "en") -> bool:
    patients = Patient.objects.filter(is_active=True).order_by("name")
    rows = []
    for p in patients:
        rows.append(
            {
                "id": f"patient_{p.id}",
                "title": _get_message(f"patient_{p.id}_name", lang, default=p.name)[:24],
                "description": _get_message(
                    f"patient_{p.id}_desc",
                    lang,
                    hospital=p.hospital,
                    remaining=f"{max(p.goal_amount - p.raised_amount, 0):,.0f}",
                )[:72],
            }
        )
    sections = [{"title": _get_message("patient_list_header", lang), "rows": rows}]
    return bool(rows) and bool(
        whatsapp_service.send_interactive_list(
            phone_number,
            _get_message("patient_list_body", lang),
            _get_message("patient_list_button", lang),
            sections,
            header_text=_get_message("medical_assistance_header", lang),
            footer_text="❤️ Thaagam Foundation",
        )
    )


def send_optional_packages(phone_number: str, lang: str = "en") -> None:
    packages = Package.objects.filter(is_active=True, category__in=["FOOD", "ALL"]).order_by(
        "display_order", "name"
    )
    rows = []
    for pkg in packages:
        desc = pkg.description or ""
        if desc:
            description = _get_message(
                f"package_{pkg.id}_desc_with_details", lang, price=pkg.price, details=desc
            )
        else:
            description = _get_message(f"package_{pkg.id}_desc", lang, price=pkg.price)
        rows.append(
            {
                "id": f"pkg_{pkg.id}",
                "title": _get_message(f"package_{pkg.id}_name", lang, default=pkg.name)[:24],
                "description": description[:72],
            }
        )

    sections = [{"title": _get_message("optional_packages_header", lang), "rows": rows[:10]}]

    if rows:
        # We still send a list for visibility; selection via typing numbers is handled by state.
        whatsapp_service.send_interactive_list(
            phone_number,
            _get_message("optional_packages_body", lang),
            _get_message("optional_packages_button", lang),
            sections,
            header_text=_get_message("optional_packages_header", lang),
            footer_text=_get_message("footer_text", lang),
        )
    else:
        whatsapp_service.send_text_message(
            phone_number,
            _get_message("no_packages_available", lang),
        )


def parse_package_selection(text: str) -> List[int]:
    t = (text or "").strip().lower()
    if t in {"skip", "skipped", "none"}:
        return []
    nums = [x.strip() for x in t.split(",") if x.strip()]
    ids: List[int] = []
    for n in nums:
        if n.isdigit():
            ids.append(int(n))
    return ids
