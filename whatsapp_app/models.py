from django.db import models
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)


# =============================================
# CATALOG MODELS — Food, Student, Patient, Package
# =============================================

class FoodItem(models.Model):
    """Food items available for donation"""

    name = models.CharField(
        max_length=100,
        help_text="Name of the food item (e.g. 'Feed a Homeless Person')"
    )
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit in INR"
    )
    unit_label = models.CharField(
        max_length=30,
        default='Person',
        help_text="Unit label (e.g. Person, Bottle, Plate)"
    )
    description = models.TextField(
        blank=True, null=True,
        help_text="Short description of the food item"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this item is currently available"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which items appear in the flow"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Food Item"
        verbose_name_plural = "Food Items"

    def __str__(self):
        return f"{self.name} — ₹{self.price_per_unit}/{self.unit_label}"


class Student(models.Model):
    """Students available for education sponsorship"""

    name = models.CharField(
        max_length=100,
        help_text="Full name of the student"
    )
    age = models.PositiveIntegerField(
        help_text="Age of the student"
    )
    school = models.CharField(
        max_length=200,
        help_text="Name of the school"
    )
    class_name = models.CharField(
        max_length=50,
        help_text="Class/Standard (e.g. '8th Standard')"
    )
    location = models.CharField(
        max_length=100,
        help_text="City/town of the student"
    )
    description = models.TextField(
        blank=True, null=True,
        help_text="Additional details about the student"
    )
    photo_url = models.URLField(
        blank=True, null=True,
        help_text="Photo URL of the student"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this student is currently accepting donations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.name} — {self.class_name}, {self.school}"


class Patient(models.Model):
    """Patients needing medical financial assistance"""

    name = models.CharField(
        max_length=100,
        help_text="Full name of the patient"
    )
    hospital = models.CharField(
        max_length=200,
        help_text="Name of the hospital"
    )
    location = models.CharField(
        max_length=100,
        help_text="City/town of the hospital"
    )
    goal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount needed in INR"
    )
    raised_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Amount raised so far in INR"
    )
    description = models.TextField(
        blank=True, null=True,
        help_text="Medical condition / reason for fundraising"
    )
    photo_url = models.URLField(
        blank=True, null=True,
        help_text="Photo URL of the patient"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this patient is currently accepting donations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    def __str__(self):
        return f"{self.name} — ₹{self.raised_amount}/₹{self.goal_amount}"

    @property
    def progress_percent(self):
        if self.goal_amount > 0:
            return round(float(self.raised_amount) / float(self.goal_amount) * 100, 1)
        return 0.0

    @property
    def remaining_amount(self):
        return max(self.goal_amount - self.raised_amount, 0)


class Package(models.Model):
    """Add-on packages donors can select"""

    CATEGORY_CHOICES = [
        ('FOOD', 'Food'),
        ('EDUCATION', 'Education'),
        ('MEDICAL', 'Medical'),
        ('ALL', 'All Categories'),
    ]

    name = models.CharField(
        max_length=100,
        help_text="Package name (e.g. 'Get a Banner')"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Package price in INR"
    )
    description = models.TextField(
        blank=True, null=True,
        help_text="Description of what the package includes"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='ALL',
        help_text="Which donation category this package applies to"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this package is currently available"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order in the flow"
    )
    image_url = models.URLField(
        max_length=500,
        blank=True, null=True,
        help_text="Public URL of the package image"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Package"
        verbose_name_plural = "Packages"

    def __str__(self):
        return f"{self.name} — ₹{self.price} ({self.get_category_display()})"


# =============================================
# DONATION MODEL — Extended
# =============================================

class Donation(models.Model):
    """Model to store all donation records for Thaagam Foundation"""

    # Donation Category Choices
    CATEGORY_CHOICES = [
        ('FOOD', '🍲 Food Donation'),
        ('EDUCATION', '📚 Education Support'),
        ('MEDICAL', '🏥 Medical Assistance'),
    ]

    # Donation Cause Choices (kept for backward compatibility)
    CAUSE_CHOICES = [
        ('FOOD', '🍲 Food Donation'),
        ('EDUCATION', '📚 Education Support'),
        ('MEDICAL', '🏥 Medical Assistance'),
        ('ORPHANAGE', '🏡 Orphanage Support'),
        ('ANIMAL', '🐾 Animal Welfare'),
        ('ENVIRONMENTAL', '🌿 Environmental Projects'),
    ]

    # Payment Status Choices
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', '⏳ Pending'),
        ('INITIATED', '🔄 Payment Initiated'),
        ('COMPLETED', '✅ Completed'),
        ('FAILED', '❌ Failed'),
        ('REFUNDED', '🔄 Refunded'),
    ]

    # Payment Method Choices
    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('EASEBUZZ', 'Easebuzz'),
        ('RAZORPAY', 'Razorpay'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]

    # Reference & Tracking
    reference_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Unique reference number for the donation"
    )
    whatsapp_phone_number = models.CharField(
        max_length=20,
        db_index=True,
        help_text="WhatsApp phone number of the donor"
    )

    # Category & Cause
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True, null=True,
        help_text="Donation category (Food/Education/Medical)"
    )
    cause = models.CharField(
        max_length=20,
        choices=CAUSE_CHOICES,
        help_text="Selected donation cause"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Donation amount in INR"
    )

    # Donor Information
    full_name = models.CharField(
        max_length=100,
        help_text="Full name of the donor"
    )
    mobile_number = models.CharField(
        max_length=15,
        help_text="Mobile number of the donor"
    )
    email = models.EmailField(
        help_text="Email address of the donor"
    )
    instagram_id = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="Instagram ID of the donor (optional)"
    )
    message = models.TextField(
        blank=True, null=True,
        help_text="Optional message from the donor"
    )

    # Linked entities
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='donations',
        help_text="Linked student (for education donations)"
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='donations',
        help_text="Linked patient (for medical donations)"
    )

    # Payment Information
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True, null=True,
        help_text="Selected payment method"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        help_text="Current payment status"
    )
    payment_id = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text="Payment gateway transaction ID"
    )
    payment_response = models.JSONField(
        blank=True, null=True,
        help_text="Full payment gateway response"
    )

    # Easebuzz fields
    easebuzz_txnid = models.CharField(
        max_length=50,
        blank=True, null=True,
        db_index=True,
        help_text="Easebuzz transaction ID"
    )
    easebuzz_access_key = models.CharField(
        max_length=200,
        blank=True, null=True,
        help_text="Easebuzz payment access key"
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when donation was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when donation was last updated"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference_number']),
            models.Index(fields=['whatsapp_phone_number']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['easebuzz_txnid']),
        ]
        verbose_name = "Donation"
        verbose_name_plural = "Donations"

    def save(self, *args, **kwargs):
        """Generate reference number before saving"""
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        # Sync category from cause if not set
        if not self.category and self.cause:
            if self.cause in ('FOOD', 'EDUCATION', 'MEDICAL'):
                self.category = self.cause
        super().save(*args, **kwargs)

    @staticmethod
    def generate_reference_number():
        """Generate a unique reference number for the donation"""
        timestamp = timezone.now().strftime('%Y%m%d')
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"THG-{timestamp}-{unique_id}"

    def get_cause_emoji(self):
        """Get emoji for the cause"""
        emoji_map = {
            'FOOD': '🍲',
            'EDUCATION': '📚',
            'MEDICAL': '🏥',
            'ORPHANAGE': '🏡',
            'ANIMAL': '🐾',
            'ENVIRONMENTAL': '🌿',
        }
        return emoji_map.get(self.cause, '❤️')

    def __str__(self):
        return f"{self.reference_number} - {self.full_name} - ₹{self.amount}"

    def get_payment_summary(self):
        """Get formatted payment summary for WhatsApp"""
        return f"""
📋 *Donation Summary*

🔖 *Reference:* {self.reference_number}
🎯 *Cause:* {self.get_cause_display()}
💰 *Amount:* ₹{self.amount}
👤 *Name:* {self.full_name}
📱 *Mobile:* {self.mobile_number}
✉️ *Email:* {self.email}
💬 *Message:* {self.message or 'N/A'}
⏰ *Date:* {self.created_at.strftime('%d-%m-%Y %H:%M')}
        """


class DonationItem(models.Model):
    """Individual items within a donation (food items, etc.)"""

    ITEM_TYPE_CHOICES = [
        ('FOOD', 'Food Item'),
        ('STUDENT', 'Student Sponsorship'),
        ('PATIENT', 'Patient Support'),
    ]

    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Parent donation"
    )
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        help_text="Type of item"
    )
    item_name = models.CharField(
        max_length=200,
        help_text="Name of the item for display"
    )
    item_id = models.PositiveIntegerField(
        help_text="ID of the related model (FoodItem, Student, Patient)"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity selected"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit at time of donation"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity × unit_price"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['item_type', 'item_name']
        verbose_name = "Donation Item"
        verbose_name_plural = "Donation Items"

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} × {self.quantity} = ₹{self.subtotal}"


class DonationPackage(models.Model):
    """Packages selected as part of a donation"""

    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name='packages',
        help_text="Parent donation"
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        help_text="Selected package"
    )
    package_name = models.CharField(
        max_length=100,
        help_text="Package name at time of donation"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Package price at time of donation"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Donation Package"
        verbose_name_plural = "Donation Packages"

    def __str__(self):
        return f"{self.package_name} — ₹{self.price}"


# =============================================
# SESSION & LOG MODELS — Existing
# =============================================

class WhatsAppSession(models.Model):
    """Track WhatsApp user sessions for better user experience"""

    whatsapp_phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="WhatsApp phone number of the user"
    )
    current_state = models.CharField(
        max_length=50,
        default='MENU',
        help_text="Current state of the conversation"
    )
    session_data = models.JSONField(
        default=dict,
        help_text="Additional session data"
    )
    last_interaction = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of last interaction"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when session was created"
    )

    class Meta:
        ordering = ['-last_interaction']
        verbose_name = "WhatsApp Session"
        verbose_name_plural = "WhatsApp Sessions"

    def __str__(self):
        return f"{self.whatsapp_phone_number} - {self.current_state}"


class WhatsAppWebhookLog(models.Model):
    """Log all incoming webhook requests for debugging and audit"""

    webhook_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique ID for the webhook request"
    )
    payload = models.JSONField(
        help_text="Full webhook payload"
    )
    processed = models.BooleanField(
        default=False,
        help_text="Whether the webhook was processed"
    )
    error_message = models.TextField(
        blank=True, null=True,
        help_text="Error message if processing failed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when webhook was received"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Webhook Log"
        verbose_name_plural = "Webhook Logs"

    def __str__(self):
        return f"{self.webhook_id} - {self.created_at}"


# =============================================
# CONVERSATION MESSAGE LOG — For Dashboard
# =============================================

class ConversationMessage(models.Model):
    """Log every incoming and outgoing WhatsApp message for dashboard display."""

    DIRECTION_CHOICES = [
        ('IN', 'Incoming'),
        ('OUT', 'Outgoing'),
    ]

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('button', 'Button Reply'),
        ('list', 'List Selection'),
        ('flow', 'Flow Response'),
        ('interactive', 'Interactive'),
        ('image', 'Image'),
        ('system', 'System'),
    ]

    phone_number = models.CharField(
        max_length=20,
        db_index=True,
        help_text="WhatsApp phone number"
    )
    direction = models.CharField(
        max_length=3,
        choices=DIRECTION_CHOICES,
        help_text="IN = user sent, OUT = bot sent"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        help_text="Type of message"
    )
    content = models.TextField(
        help_text="Message body or selection text"
    )
    metadata = models.JSONField(
        blank=True, null=True,
        help_text="Extra data (button_id, list_id, flow data, etc.)"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the message was sent/received"
    )

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['phone_number', 'timestamp']),
        ]
        verbose_name = "Conversation Message"
        verbose_name_plural = "Conversation Messages"

    def __str__(self):
        arrow = "→" if self.direction == 'OUT' else "←"
        return f"{arrow} {self.phone_number} [{self.message_type}] {self.content[:50]}"