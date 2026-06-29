from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from whatsapp_app.models import FoodItem, Package, Patient, Student
from whatsapp_app.whatsapp_service import whatsapp_service


def send_food_items_list(phone_number: str) -> bool:
    items = FoodItem.objects.filter(is_active=True).order_by("display_order", "name")
    rows = []
    for it in items:
        rows.append(
            {
                "id": f"food_{it.id}",
                "title": (it.name or "").strip()[:24],
                "description": f"₹{it.price_per_unit}/{it.unit_label}"[:72],
            }
        )
    sections = [{"title": "🍽️ Available Food Items", "rows": rows}]
    return bool(rows) and bool(
        whatsapp_service.send_interactive_list(
            phone_number,
            "Please select a food item:",
            "Select Food",
            sections,
            header_text="🍛 Food Donation",
            footer_text="❤️ Thaagam Foundation",
        )
    )


def send_student_list(phone_number: str) -> bool:
    students = Student.objects.filter(is_active=True).order_by("name")
    rows = []
    for s in students:
        rows.append(
            {
                "id": f"student_{s.id}",
                "title": (s.name or "").strip()[:24],
                "description": f"{s.class_name}, {s.school}"[:72],
            }
        )
    sections = [{"title": "🎓 Students List", "rows": rows}]
    return bool(rows) and bool(
        whatsapp_service.send_interactive_list(
            phone_number,
            "Please select a student to sponsor:",
            "Select Student",
            sections,
            header_text="🎓 Education Sponsorship",
            footer_text="❤️ Thaagam Foundation",
        )
    )


def send_patient_list(phone_number: str) -> bool:
    patients = Patient.objects.filter(is_active=True).order_by("name")
    rows = []
    for p in patients:
        rows.append(
            {
                "id": f"patient_{p.id}",
                "title": (p.name or "").strip()[:24],
                "description": f"{p.hospital} | Remaining: ₹{max(p.goal_amount-p.raised_amount,0):,.0f}"[:72],
            }
        )
    sections = [{"title": "🏥 Patients List", "rows": rows}]
    return bool(rows) and bool(
        whatsapp_service.send_interactive_list(
            phone_number,
            "Please select a patient to support:",
            "Select Patient",
            sections,
            header_text="🏥 Medical Assistance",
            footer_text="❤️ Thaagam Foundation",
        )
    )


def send_optional_packages(phone_number: str) -> None:
    packages = Package.objects.filter(is_active=True, category__in=["FOOD", "ALL"]).order_by(
        "display_order", "name"
    )
    rows = []
    for pkg in packages:
        desc = pkg.description or ""
        if desc:
            description = f"₹{pkg.price} - {desc}"
        else:
            description = f"₹{pkg.price}"
        rows.append(
            {
                "id": f"pkg_{pkg.id}",
                "title": (pkg.name or "").strip()[:24],
                "description": description[:72],
            }
        )

    sections = [{"title": "🎁 Extra Packages (Optional)", "rows": rows[:10]}]

    if rows:
        whatsapp_service.send_text_message(
            phone_number,
            "🎁 Extra Packages (Optional)\n\n"
            "Select ONE or MORE packages by typing their numbers (comma-separated), OR type 'skip'.\n\n"
            "Example: 1,3,5\n\n"
            "You can also type 'menu' anytime.",
        )
        # We still send a list for visibility; selection via typing numbers is handled by state.
        whatsapp_service.send_interactive_list(
            phone_number,
            "Available packages:",
            "Select Package",
            sections,
            header_text="🎁 Food Packages",
            footer_text="❤️ Thaagam Foundation",
        )
    else:
        whatsapp_service.send_text_message(
            phone_number,
            "No extra packages are available right now. Type *skip* to continue.",
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

