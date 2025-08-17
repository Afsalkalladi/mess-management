"""
Database models for Mess Management System
Implements all entities with proper relationships and constraints
"""

from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.contrib.postgres.fields import DateRangeField
import hashlib
import hmac
import secrets
from datetime import date, datetime
from typing import Optional


class StudentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    DENIED = 'DENIED', 'Denied'


class PaymentStatus(models.TextChoices):
    NONE = 'NONE', 'None'
    UPLOADED = 'UPLOADED', 'Uploaded'
    VERIFIED = 'VERIFIED', 'Verified'
    DENIED = 'DENIED', 'Denied'


class PaymentSource(models.TextChoices):
    ONLINE_SCREENSHOT = 'ONLINE_SCREENSHOT', 'Online Screenshot'
    OFFLINE_MANUAL = 'OFFLINE_MANUAL', 'Offline Manual'


class MealType(models.TextChoices):
    BREAKFAST = 'BREAKFAST', 'Breakfast'
    LUNCH = 'LUNCH', 'Lunch'
    DINNER = 'DINNER', 'Dinner'


class ScanResult(models.TextChoices):
    ALLOWED = 'ALLOWED', 'Allowed'
    BLOCKED_NO_PAYMENT = 'BLOCKED_NO_PAYMENT', 'Blocked - No Payment'
    BLOCKED_CUT = 'BLOCKED_CUT', 'Blocked - Mess Cut'
    BLOCKED_STATUS = 'BLOCKED_STATUS', 'Blocked - Status'
    BLOCKED_CLOSURE = 'BLOCKED_CLOSURE', 'Blocked - Mess Closure'


class ActorType(models.TextChoices):
    STUDENT = 'STUDENT', 'Student'
    ADMIN = 'ADMIN', 'Admin'
    STAFF = 'STAFF', 'Staff'
    SYSTEM = 'SYSTEM', 'System'


class Student(models.Model):
    """Student entity with QR code management"""
    
    tg_user_id = models.BigIntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=100)
    roll_no = models.CharField(max_length=20, unique=True, db_index=True)
    room_no = models.CharField(max_length=20)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    status = models.CharField(
        max_length=10,
        choices=StudentStatus.choices,
        default=StudentStatus.PENDING,
        db_index=True
    )
    qr_version = models.IntegerField(default=1)
    qr_nonce = models.CharField(max_length=64, default=secrets.token_hex)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'students'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
    
    def generate_qr_payload(self, secret: str) -> str:
        """Generate HMAC-signed QR payload"""
        data = f"v|{self.id}|{self.qr_version}|{self.qr_nonce}"
        signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{data}|{signature}"
    
    def regenerate_qr(self):
        """Regenerate QR by updating nonce and version"""
        self.qr_version += 1
        self.qr_nonce = secrets.token_hex(32)
        self.save(update_fields=['qr_version', 'qr_nonce', 'updated_at'])
    
    def has_valid_payment(self, for_date: Optional[date] = None) -> bool:
        """Check if student has valid payment for given date"""
        check_date = for_date or timezone.now().date()
        return self.payments.filter(
            status=PaymentStatus.VERIFIED,
            cycle_start__lte=check_date,
            cycle_end__gte=check_date
        ).exists()
    
    def __str__(self):
        return f"{self.name} ({self.roll_no})"


class Payment(models.Model):
    """Payment records with verification workflow"""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    cycle_start = models.DateField()
    cycle_end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    screenshot_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NONE,
        db_index=True
    )
    source = models.CharField(
        max_length=20,
        choices=PaymentSource.choices,
        default=PaymentSource.ONLINE_SCREENSHOT
    )
    reviewer_admin_id = models.BigIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'cycle_start', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def verify(self, admin_id: int):
        """Verify payment"""
        self.status = PaymentStatus.VERIFIED
        self.reviewer_admin_id = admin_id
        self.reviewed_at = timezone.now()
        self.save()
    
    def deny(self, admin_id: int):
        """Deny payment"""
        self.status = PaymentStatus.DENIED
        self.reviewer_admin_id = admin_id
        self.reviewed_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Payment {self.student.roll_no} ({self.cycle_start} - {self.cycle_end})"


class MessCut(models.Model):
    """Mess cut applications with cutoff enforcement"""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='mess_cuts'
    )
    from_date = models.DateField(db_index=True)
    to_date = models.DateField(db_index=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    applied_by = models.CharField(
        max_length=20,
        choices=[
            ('STUDENT', 'Student'),
            ('ADMIN_SYSTEM', 'Admin System')
        ],
        default='STUDENT'
    )
    cutoff_ok = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'mess_cuts'
        ordering = ['-from_date']
        indexes = [
            models.Index(fields=['student', 'from_date', 'to_date']),
            models.Index(fields=['from_date', 'to_date']),
        ]
    
    def clean(self):
        """Validate date range"""
        if self.from_date > self.to_date:
            raise ValueError("From date must be before or equal to end date")
    
    def is_active_on(self, check_date: date) -> bool:
        """Check if cut is active on given date"""
        return self.from_date <= check_date <= self.to_date
    
    def __str__(self):
        return f"Cut {self.student.roll_no} ({self.from_date} - {self.to_date})"


class MessClosure(models.Model):
    """Admin-declared mess closures"""
    
    from_date = models.DateField(db_index=True)
    to_date = models.DateField(db_index=True)
    reason = models.TextField(blank=True)
    created_by_admin_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mess_closures'
        ordering = ['-from_date']
        indexes = [
            models.Index(fields=['from_date', 'to_date']),
        ]
    
    def is_active_on(self, check_date: date) -> bool:
        """Check if closure is active on given date"""
        return self.from_date <= check_date <= self.to_date
    
    def __str__(self):
        return f"Closure ({self.from_date} - {self.to_date})"


class ScanEvent(models.Model):
    """QR scan events with access control logging"""
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='scan_events'
    )
    meal = models.CharField(max_length=10, choices=MealType.choices)
    scanned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    staff_token_id = models.ForeignKey(
        'StaffToken',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    result = models.CharField(
        max_length=30,
        choices=ScanResult.choices
    )
    device_info = models.TextField(blank=True)
    
    class Meta:
        db_table = 'scan_events'
        ordering = ['-scanned_at']
        indexes = [
            models.Index(fields=['student', 'scanned_at']),
            models.Index(fields=['scanned_at', 'meal']),
        ]
        # Prevent duplicate scans within short time window
        unique_together = [['student', 'meal', 'scanned_at']]
    
    def __str__(self):
        return f"Scan {self.student.roll_no} - {self.meal} ({self.scanned_at})"


class StaffToken(models.Model):
    """Revocable staff authentication tokens"""
    
    label = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'staff_tokens'
        ordering = ['-issued_at']
    
    @classmethod
    def create_token(cls, label: str, expires_at: Optional[datetime] = None) -> tuple:
        """Create new token and return (token, instance)"""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        instance = cls.objects.create(
            label=label,
            token_hash=token_hash,
            expires_at=expires_at
        )
        return raw_token, instance
    
    def is_valid(self) -> bool:
        """Check if token is still valid"""
        if not self.active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
    
    def record_usage(self):
        """Update last used timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def __str__(self):
        return f"Token: {self.label}"


class AuditLog(models.Model):
    """Comprehensive audit trail for all critical operations"""
    
    actor_type = models.CharField(max_length=10, choices=ActorType.choices)
    actor_id = models.CharField(max_length=50, blank=True)
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor_type', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
        ]
    
    @classmethod
    def log(cls, actor_type: str, actor_id: str, event_type: str, **payload):
        """Create audit log entry"""
        return cls.objects.create(
            actor_type=actor_type,
            actor_id=str(actor_id),
            event_type=event_type,
            payload=payload
        )
    
    def __str__(self):
        return f"{self.event_type} by {self.actor_type}:{self.actor_id}"


class Settings(models.Model):
    """Singleton settings model for system configuration"""
    
    tz = models.CharField(max_length=50, default='Asia/Kolkata')
    cutoff_time = models.TimeField(default='23:00')
    qr_secret_version = models.IntegerField(default=1)
    qr_secret_hash = models.CharField(max_length=64)
    meals = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'settings'
    
    def save(self, *args, **kwargs):
        """Ensure only one settings instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create settings instance"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def __str__(self):
        return "System Settings"


class DLQLog(models.Model):
    """Dead Letter Queue for failed operations"""
    
    operation = models.CharField(max_length=100)
    payload = models.JSONField()
    error_message = models.TextField()
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'dlq_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['resolved', 'created_at']),
        ]
    
    def can_retry(self) -> bool:
        """Check if operation can be retried"""
        return not self.resolved and self.retry_count < self.max_retries
    
    def __str__(self):
        return f"DLQ: {self.operation} ({self.retry_count}/{self.max_retries})"