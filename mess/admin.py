"""
Django Admin configuration for Mess Management System
Provides admin interface for managing all models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Student, Payment, MessCut, MessClosure,
    ScanEvent, StaffToken, AuditLog, Settings, DLQLog
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin interface for Student model"""
    
    list_display = ['roll_no', 'name', 'room_no', 'status', 'qr_version', 'created_at']
    list_filter = ['status', 'created_at', 'qr_version']
    search_fields = ['name', 'roll_no', 'room_no', 'phone', 'tg_user_id']
    readonly_fields = ['tg_user_id', 'qr_nonce', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'roll_no', 'room_no', 'phone')
        }),
        ('Telegram', {
            'fields': ('tg_user_id',)
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('QR Code', {
            'fields': ('qr_version', 'qr_nonce'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_students', 'deny_students', 'regenerate_qr']
    
    def approve_students(self, request, queryset):
        """Bulk approve students"""
        updated = queryset.filter(status='PENDING').update(status='APPROVED')
        self.message_user(request, f'{updated} students approved.')
    approve_students.short_description = "Approve selected students"
    
    def deny_students(self, request, queryset):
        """Bulk deny students"""
        updated = queryset.filter(status='PENDING').update(status='DENIED')
        self.message_user(request, f'{updated} students denied.')
    deny_students.short_description = "Deny selected students"
    
    def regenerate_qr(self, request, queryset):
        """Regenerate QR codes"""
        for student in queryset:
            student.regenerate_qr()
        self.message_user(request, f'QR codes regenerated for {queryset.count()} students.')
    regenerate_qr.short_description = "Regenerate QR codes"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model"""
    
    list_display = ['student_roll', 'cycle_dates', 'amount', 'status', 'source', 'created_at']
    list_filter = ['status', 'source', 'created_at', 'cycle_start']
    search_fields = ['student__name', 'student__roll_no']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at']
    date_hierarchy = 'cycle_start'
    
    fieldsets = (
        ('Student', {
            'fields': ('student',)
        }),
        ('Payment Details', {
            'fields': ('cycle_start', 'cycle_end', 'amount', 'screenshot_url')
        }),
        ('Verification', {
            'fields': ('status', 'source', 'reviewer_admin_id', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['verify_payments', 'deny_payments']
    
    def student_roll(self, obj):
        """Display student roll number"""
        return obj.student.roll_no
    student_roll.short_description = 'Roll No'
    
    def cycle_dates(self, obj):
        """Display payment cycle"""
        return f"{obj.cycle_start} to {obj.cycle_end}"
    cycle_dates.short_description = 'Cycle'
    
    def verify_payments(self, request, queryset):
        """Bulk verify payments"""
        updated = queryset.filter(status='UPLOADED').update(
            status='VERIFIED',
            reviewer_admin_id=request.user.id if hasattr(request.user, 'id') else 0,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} payments verified.')
    verify_payments.short_description = "Verify selected payments"
    
    def deny_payments(self, request, queryset):
        """Bulk deny payments"""
        updated = queryset.filter(status='UPLOADED').update(
            status='DENIED',
            reviewer_admin_id=request.user.id if hasattr(request.user, 'id') else 0,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} payments denied.')
    deny_payments.short_description = "Deny selected payments"


@admin.register(MessCut)
class MessCutAdmin(admin.ModelAdmin):
    """Admin interface for MessCut model"""
    
    list_display = ['student_roll', 'date_range', 'applied_by', 'cutoff_ok', 'applied_at']
    list_filter = ['applied_by', 'cutoff_ok', 'from_date', 'applied_at']
    search_fields = ['student__name', 'student__roll_no']
    date_hierarchy = 'from_date'
    readonly_fields = ['applied_at']
    
    def student_roll(self, obj):
        """Display student roll number"""
        return obj.student.roll_no
    student_roll.short_description = 'Roll No'
    
    def date_range(self, obj):
        """Display cut date range"""
        return f"{obj.from_date} to {obj.to_date}"
    date_range.short_description = 'Date Range'


@admin.register(MessClosure)
class MessClosureAdmin(admin.ModelAdmin):
    """Admin interface for MessClosure model"""
    
    list_display = ['date_range', 'reason', 'created_by_admin_id', 'created_at']
    list_filter = ['from_date', 'created_at']
    search_fields = ['reason']
    date_hierarchy = 'from_date'
    readonly_fields = ['created_at']
    
    def date_range(self, obj):
        """Display closure date range"""
        return f"{obj.from_date} to {obj.to_date}"
    date_range.short_description = 'Date Range'


@admin.register(ScanEvent)
class ScanEventAdmin(admin.ModelAdmin):
    """Admin interface for ScanEvent model"""
    
    list_display = ['student_roll', 'meal', 'result', 'scanned_at', 'staff_token_id']
    list_filter = ['meal', 'result', 'scanned_at']
    search_fields = ['student__name', 'student__roll_no']
    date_hierarchy = 'scanned_at'
    readonly_fields = ['scanned_at']
    
    def student_roll(self, obj):
        """Display student roll number"""
        return obj.student.roll_no
    student_roll.short_description = 'Roll No'


@admin.register(StaffToken)
class StaffTokenAdmin(admin.ModelAdmin):
    """Admin interface for StaffToken model"""

    list_display = ['label', 'token_hash_short', 'active', 'issued_at', 'expires_at', 'last_used_at']
    list_filter = ['active', 'issued_at', 'expires_at']
    search_fields = ['label']
    readonly_fields = ['token_hash', 'issued_at', 'last_used_at', 'raw_token_display']

    actions = ['deactivate_tokens', 'activate_tokens']

    def token_hash_short(self, obj):
        if obj.token_hash:
            return f"{obj.token_hash[:8]}..."
        return "Not set"
    token_hash_short.short_description = "Token Hash"

    def raw_token_display(self, obj):
        if hasattr(obj, '_raw_token'):
            return f"🔑 {obj._raw_token}"
        return "Token will be generated on save"
    raw_token_display.short_description = "Raw Token (Save this!)"

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new token
            from datetime import datetime, timedelta
            from django.utils import timezone

            # Set default expiry to 1 year if not set
            if not obj.expires_at:
                obj.expires_at = timezone.now() + timedelta(days=365)

            # Generate token using the class method
            raw_token, obj = StaffToken.create_token(
                label=obj.label,
                expires_at=obj.expires_at
            )

            # Store raw token temporarily for display
            obj._raw_token = raw_token

            # Add success message with token
            from django.contrib import messages
            messages.success(
                request,
                f'Staff token created successfully! '
                f'Token: {raw_token} '
                f'(Save this token - it will not be shown again!)'
            )
        else:
            super().save_model(request, obj, form, change)

    def deactivate_tokens(self, request, queryset):
        """Deactivate tokens"""
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} tokens deactivated.')
    deactivate_tokens.short_description = "Deactivate selected tokens"

    def activate_tokens(self, request, queryset):
        """Activate tokens"""
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} tokens activated.')
    activate_tokens.short_description = "Activate selected tokens"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model"""
    
    list_display = ['event_type', 'actor_type', 'actor_id', 'created_at']
    list_filter = ['actor_type', 'event_type', 'created_at']
    search_fields = ['event_type', 'actor_id']
    date_hierarchy = 'created_at'
    readonly_fields = ['actor_type', 'actor_id', 'event_type', 'payload', 'created_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs"""
        return request.user.is_superuser


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    """Admin interface for Settings model"""
    
    list_display = ['tz', 'cutoff_time', 'qr_secret_version']
    fieldsets = (
        ('Timezone', {
            'fields': ('tz', 'cutoff_time')
        }),
        ('QR Configuration', {
            'fields': ('qr_secret_version', 'qr_secret_hash')
        }),
        ('Meal Timings', {
            'fields': ('meals',),
            'description': 'JSON configuration for meal timings'
        })
    )
    
    def has_add_permission(self, request):
        """Only allow one settings instance"""
        return not Settings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings"""
        return False


@admin.register(DLQLog)
class DLQLogAdmin(admin.ModelAdmin):
    """Admin interface for DLQLog model"""
    
    list_display = ['operation', 'retry_status', 'error_summary', 'created_at', 'resolved']
    list_filter = ['resolved', 'operation', 'created_at']
    search_fields = ['operation', 'error_message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'last_retry_at']
    
    actions = ['retry_operations', 'mark_resolved']
    
    def retry_status(self, obj):
        """Display retry status"""
        return f"{obj.retry_count}/{obj.max_retries}"
    retry_status.short_description = 'Retries'
    
    def error_summary(self, obj):
        """Display error summary"""
        return obj.error_message[:50] + '...' if len(obj.error_message) > 50 else obj.error_message
    error_summary.short_description = 'Error'
    
    def retry_operations(self, request, queryset):
        """Retry failed operations"""
        from .tasks import process_dlq_retries
        process_dlq_retries.delay()
        self.message_user(request, 'Retry task queued.')
    retry_operations.short_description = "Retry selected operations"
    
    def mark_resolved(self, request, queryset):
        """Mark as resolved"""
        updated = queryset.update(resolved=True)
        self.message_user(request, f'{updated} entries marked as resolved.')
    mark_resolved.short_description = "Mark as resolved"


# Admin site customization
admin.site.site_header = "Mess Management System"
admin.site.site_title = "Mess Admin"
admin.site.index_title = "Administration Dashboard"