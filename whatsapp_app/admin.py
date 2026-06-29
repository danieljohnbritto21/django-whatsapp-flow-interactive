from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Donation, WhatsAppSession, WhatsAppWebhookLog,
    FoodItem, Student, Patient, Package, DonationItem, DonationPackage
)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_per_unit', 'unit_label', 'is_active', 'display_order']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'class_name', 'school', 'is_active']
    list_filter = ['is_active', 'class_name']
    search_fields = ['name', 'school', 'location']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'hospital', 'raised_amount', 'goal_amount', 'progress', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'hospital', 'location']
    
    def progress(self, obj):
        return f"{obj.progress_percent}%"
    progress.short_description = "Progress"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'is_active', 'display_order']
    list_filter = ['category', 'is_active']
    search_fields = ['name']


class DonationItemInline(admin.TabularInline):
    model = DonationItem
    extra = 0
    readonly_fields = ['item_type', 'item_name', 'item_id', 'quantity', 'unit_price', 'subtotal']
    can_delete = False


class DonationPackageInline(admin.TabularInline):
    model = DonationPackage
    extra = 0
    readonly_fields = ['package_name', 'price']
    can_delete = False


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = [
        'reference_number', 
        'full_name', 
        'amount_display', 
        'category',
        'cause_display',
        'payment_status_display',
        'created_at'
    ]
    list_filter = ['category', 'cause', 'payment_status', 'payment_method', 'created_at']
    search_fields = [
        'reference_number', 
        'full_name', 
        'mobile_number', 
        'email', 
        'whatsapp_phone_number',
        'easebuzz_txnid'
    ]
    readonly_fields = ['reference_number', 'created_at', 'updated_at', 'easebuzz_txnid', 'easebuzz_access_key']
    inlines = [DonationItemInline, DonationPackageInline]
    
    fieldsets = (
        ('Reference Information', {
            'fields': ('reference_number', 'whatsapp_phone_number')
        }),
        ('Donation Details', {
            'fields': ('category', 'cause', 'amount', 'student', 'patient')
        }),
        ('Donor Information', {
            'fields': ('full_name', 'mobile_number', 'email', 'instagram_id', 'message')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'payment_id', 'easebuzz_txnid', 'easebuzz_access_key', 'payment_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return f"₹{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def cause_display(self, obj):
        return obj.get_cause_display()
    cause_display.short_description = 'Cause'
    
    def payment_status_display(self, obj):
        status_colors = {
            'PENDING': 'orange',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'REFUNDED': 'blue'
        }
        color = status_colors.get(obj.payment_status, 'black')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.get_payment_status_display()}</span>')
    payment_status_display.short_description = 'Payment Status'
    
    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_refunded']
    
    def mark_as_completed(self, request, queryset):
        count = queryset.update(payment_status='COMPLETED')
        self.message_user(request, f"{count} donation(s) marked as completed.")
    mark_as_completed.short_description = "Mark selected donations as COMPLETED"
    
    def mark_as_failed(self, request, queryset):
        count = queryset.update(payment_status='FAILED')
        self.message_user(request, f"{count} donation(s) marked as failed.")
    mark_as_failed.short_description = "Mark selected donations as FAILED"
    
    def mark_as_refunded(self, request, queryset):
        count = queryset.update(payment_status='REFUNDED')
        self.message_user(request, f"{count} donation(s) marked as refunded.")
    mark_as_refunded.short_description = "Mark selected donations as REFUNDED"


@admin.register(WhatsAppSession)
class WhatsAppSessionAdmin(admin.ModelAdmin):
    list_display = ['whatsapp_phone_number', 'current_state', 'last_interaction', 'created_at']
    list_filter = ['current_state', 'created_at']
    search_fields = ['whatsapp_phone_number']
    readonly_fields = ['created_at', 'last_interaction']


@admin.register(WhatsAppWebhookLog)
class WhatsAppWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['webhook_id', 'processed', 'created_at']
    list_filter = ['processed', 'created_at']
    search_fields = ['webhook_id']
    readonly_fields = ['webhook_id', 'payload', 'processed', 'error_message', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False