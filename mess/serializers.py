"""
DRF Serializers for API endpoints
Handles validation, serialization, and business logic
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date, timedelta
from typing import Dict, Any
from .models import (
    Student, Payment, MessCut, MessClosure, 
    ScanEvent, StudentStatus, PaymentStatus,
    MealType, ScanResult
)
from core.utils import validate_qr_payload, get_current_meal


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """Student registration with validation"""
    
    class Meta:
        model = Student
        fields = ['name', 'roll_no', 'room_no', 'phone', 'tg_user_id']
        
    def validate_roll_no(self, value):
        """Ensure roll number is unique"""
        if Student.objects.filter(roll_no=value).exists():
            raise serializers.ValidationError("Roll number already registered")
        return value.upper()
    
    def validate_phone(self, value):
        """Validate phone format"""
        import re
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Invalid phone number format")
        return value


class StudentSnapshotSerializer(serializers.ModelSerializer):
    """Student info for scanner display"""
    
    payment_ok = serializers.SerializerMethodField()
    has_cut_today = serializers.SerializerMethodField()
    has_closure_today = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'roll_no', 'room_no', 
            'status', 'payment_ok', 'has_cut_today', 
            'has_closure_today'
        ]
    
    def get_payment_ok(self, obj):
        """Check if student has valid payment"""
        return obj.has_valid_payment()
    
    def get_has_cut_today(self, obj):
        """Check if student has mess cut today"""
        today = timezone.now().date()
        return obj.mess_cuts.filter(
            from_date__lte=today,
            to_date__gte=today
        ).exists()
    
    def get_has_closure_today(self, obj):
        """Check if mess is closed today"""
        today = timezone.now().date()
        return MessClosure.objects.filter(
            from_date__lte=today,
            to_date__gte=today
        ).exists()


class PaymentUploadSerializer(serializers.ModelSerializer):
    """Payment upload with screenshot"""
    
    class Meta:
        model = Payment
        fields = ['student', 'cycle_start', 'cycle_end', 'amount', 'screenshot_url']
    
    def validate(self, data):
        """Validate payment cycle dates"""
        if data['cycle_start'] > data['cycle_end']:
            raise serializers.ValidationError("Invalid cycle dates")
        
        # Check for overlapping payments
        existing = Payment.objects.filter(
            student=data['student'],
            status__in=[PaymentStatus.UPLOADED, PaymentStatus.VERIFIED]
        ).exclude(
            cycle_end__lt=data['cycle_start']
        ).exclude(
            cycle_start__gt=data['cycle_end']
        )
        
        if existing.exists():
            raise serializers.ValidationError("Overlapping payment cycle exists")
        
        return data


class PaymentVerificationSerializer(serializers.Serializer):
    """Admin payment verification"""
    
    action = serializers.ChoiceField(choices=['verify', 'deny'])
    admin_id = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Process verification action"""
        action = validated_data['action']
        admin_id = validated_data['admin_id']
        
        if action == 'verify':
            instance.verify(admin_id)
        else:
            instance.deny(admin_id)
        
        return instance


class MessCutSerializer(serializers.ModelSerializer):
    """Mess cut application with cutoff validation"""
    
    class Meta:
        model = MessCut
        fields = ['student', 'from_date', 'to_date']
    
    def validate(self, data):
        """Enforce cutoff rules"""
        now = timezone.now()
        tomorrow = (now + timedelta(days=1)).date()
        cutoff_time = datetime.strptime('23:00', '%H:%M').time()
        
        # Check cutoff for tomorrow
        if data['from_date'] <= tomorrow:
            current_time = now.time()
            if current_time > cutoff_time:
                raise serializers.ValidationError(
                    f"Cutoff time (23:00) passed for {tomorrow}. "
                    "You can only apply for dates starting day after tomorrow."
                )
        
        # Validate date range
        if data['from_date'] > data['to_date']:
            raise serializers.ValidationError("Invalid date range")
        
        # Check for past dates
        if data['to_date'] < now.date():
            raise serializers.ValidationError("Cannot apply cut for past dates")
        
        # Check for overlapping cuts
        overlapping = MessCut.objects.filter(
            student=data['student']
        ).exclude(
            to_date__lt=data['from_date']
        ).exclude(
            from_date__gt=data['to_date']
        )
        
        if overlapping.exists():
            raise serializers.ValidationError("Overlapping mess cut exists")
        
        return data


class MessClosureSerializer(serializers.ModelSerializer):
    """Admin mess closure declaration"""
    
    class Meta:
        model = MessClosure
        fields = ['from_date', 'to_date', 'reason', 'created_by_admin_id']
    
    def validate(self, data):
        """Validate closure dates"""
        if data['from_date'] > data['to_date']:
            raise serializers.ValidationError("Invalid date range")
        
        # Check for overlapping closures
        overlapping = MessClosure.objects.exclude(
            to_date__lt=data['from_date']
        ).exclude(
            from_date__gt=data['to_date']
        )
        
        if overlapping.exists():
            raise serializers.ValidationError("Overlapping closure exists")
        
        return data


class QRScanSerializer(serializers.Serializer):
    """QR scan request validation"""
    
    qr_data = serializers.CharField()
    meal = serializers.ChoiceField(choices=MealType.choices, required=False)
    device_info = serializers.CharField(required=False, allow_blank=True)
    
    def validate_qr_data(self, value):
        """Validate QR payload"""
        from django.conf import settings
        
        is_valid, student_id = validate_qr_payload(value, settings.QR_SECRET)
        if not is_valid:
            raise serializers.ValidationError("Invalid QR code")
        
        self.context['student_id'] = student_id
        return value
    
    def validate_meal(self, value):
        """Auto-detect meal if not provided"""
        if not value:
            value = get_current_meal()
            if not value:
                raise serializers.ValidationError(
                    "No meal service active. Please select meal manually."
                )
        return value
    
    def create(self, validated_data):
        """Process scan and create event"""
        student_id = self.context['student_id']
        staff_token = self.context.get('staff_token')
        
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise serializers.ValidationError("Student not found")
        
        # Determine scan result
        result = self._determine_scan_result(student)
        
        # Create scan event
        scan_event = ScanEvent.objects.create(
            student=student,
            meal=validated_data['meal'],
            staff_token_id=staff_token,
            result=result,
            device_info=validated_data.get('device_info', '')
        )
        
        return {
            'result': result,
            'student': StudentSnapshotSerializer(student).data,
            'scan_event_id': scan_event.id,
            'message': self._get_result_message(result)
        }
    
    def _determine_scan_result(self, student) -> str:
        """Determine if student can access meal"""
        today = timezone.now().date()
        
        # Check student status
        if student.status != StudentStatus.APPROVED:
            return ScanResult.BLOCKED_STATUS
        
        # Check payment
        if not student.has_valid_payment(today):
            return ScanResult.BLOCKED_NO_PAYMENT
        
        # Check mess cut
        if student.mess_cuts.filter(
            from_date__lte=today,
            to_date__gte=today
        ).exists():
            return ScanResult.BLOCKED_CUT
        
        # Check mess closure
        if MessClosure.objects.filter(
            from_date__lte=today,
            to_date__gte=today
        ).exists():
            return ScanResult.BLOCKED_CLOSURE
        
        return ScanResult.ALLOWED
    
    def _get_result_message(self, result: str) -> str:
        """Get human-readable message for scan result"""
        messages = {
            ScanResult.ALLOWED: "Access granted. Enjoy your meal!",
            ScanResult.BLOCKED_NO_PAYMENT: "Payment not verified for current cycle",
            ScanResult.BLOCKED_CUT: "Mess cut applied for today",
            ScanResult.BLOCKED_STATUS: "Student registration not approved",
            ScanResult.BLOCKED_CLOSURE: "Mess is closed today"
        }
        return messages.get(result, "Unknown error")


class ReportSerializer(serializers.Serializer):
    """Base serializer for reports"""
    
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)
    status = serializers.CharField(required=False)
    
    def validate(self, data):
        """Validate date range if provided"""
        if data.get('from_date') and data.get('to_date'):
            if data['from_date'] > data['to_date']:
                raise serializers.ValidationError("Invalid date range")
        return data


class AdminActionSerializer(serializers.Serializer):
    """Generic admin action serializer"""
    
    admin_id = serializers.IntegerField()
    action = serializers.CharField()
    target_id = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True)
    
    def validate_admin_id(self, value):
        """Verify admin ID is in allowed list"""
        from django.conf import settings
        if value not in settings.ADMIN_TG_IDS:
            raise serializers.ValidationError("Unauthorized admin ID")
        return value


class BulkQRRegenerateSerializer(serializers.Serializer):
    """Bulk QR regeneration request"""
    
    admin_id = serializers.IntegerField()
    confirm = serializers.BooleanField()
    
    def validate_confirm(self, value):
        """Ensure explicit confirmation"""
        if not value:
            raise serializers.ValidationError("Confirmation required for bulk QR regeneration")
        return value
    
    def validate_admin_id(self, value):
        """Verify admin authorization"""
        from django.conf import settings
        if value not in settings.ADMIN_TG_IDS:
            raise serializers.ValidationError("Unauthorized admin")
        return value