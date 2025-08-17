"""
API Views for Mess Management System
RESTful endpoints with proper authentication and permissions
"""

from rest_framework import status, generics, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import logging

from .models import (
    Student, Payment, MessCut, MessClosure,
    ScanEvent, StaffToken, AuditLog,
    StudentStatus, PaymentStatus
)
from .serializers import (
    StudentRegistrationSerializer, StudentSnapshotSerializer,
    PaymentUploadSerializer, PaymentVerificationSerializer,
    MessCutSerializer, MessClosureSerializer,
    QRScanSerializer, ReportSerializer,
    AdminActionSerializer, BulkQRRegenerateSerializer
)
from .permissions import IsAdmin, IsStaff
from .tasks import (
    send_telegram_notification, sync_to_google_sheets,
    process_qr_regeneration
)

logger = logging.getLogger(__name__)


class StudentRegistrationView(generics.CreateAPIView):
    """Student registration endpoint"""
    
    serializer_class = StudentRegistrationSerializer
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Register new student"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        student = serializer.save(status=StudentStatus.PENDING)
        
        # Audit log
        AuditLog.log(
            actor_type='STUDENT',
            actor_id=student.tg_user_id,
            event_type='REGISTRATION_SUBMITTED',
            student_id=student.id,
            data=serializer.validated_data
        )
        
        # Notify admins
        send_telegram_notification.delay(
            'admin_group',
            f"New registration: {student.name} ({student.roll_no})"
        )
        
        # Sync to sheets
        sync_to_google_sheets.delay('registrations', student.id)
        
        return Response(
            {"message": "Registration submitted. Awaiting admin approval."},
            status=status.HTTP_201_CREATED
        )


class StudentApprovalView(views.APIView):
    """Admin approval/denial of student registration"""
    
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def post(self, request, student_id, action):
        """Approve or deny student"""
        if action not in ['approve', 'deny']:
            return Response(
                {"error": "Invalid action"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if student.status != StudentStatus.PENDING:
            return Response(
                {"error": "Student already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        admin_id = request.data.get('admin_id')
        
        if action == 'approve':
            student.status = StudentStatus.APPROVED
            message = "Registration approved! Your QR code is being generated."
            
            # Generate QR in background
            from .utils import generate_qr_code
            qr_payload = student.generate_qr_payload(settings.QR_SECRET)
            qr_image = generate_qr_code(qr_payload)
            
            # Send QR to student
            send_telegram_notification.delay(
                student.tg_user_id,
                message,
                attachment=qr_image
            )
        else:
            student.status = StudentStatus.DENIED
            message = "Registration denied. Please contact admin if you believe this is an error."
            
            send_telegram_notification.delay(student.tg_user_id, message)
        
        student.save()
        
        # Audit log
        AuditLog.log(
            actor_type='ADMIN',
            actor_id=admin_id,
            event_type=f'REGISTRATION_{action.upper()}',
            student_id=student.id
        )
        
        # Sync to sheets
        sync_to_google_sheets.delay('registrations', student.id)
        
        return Response({"message": f"Student {action}d successfully"})


class PaymentUploadView(generics.CreateAPIView):
    """Student payment upload"""
    
    serializer_class = PaymentUploadSerializer
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Upload payment screenshot"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment = serializer.save(status=PaymentStatus.UPLOADED)
        
        # Upload to Cloudinary
        if 'screenshot' in request.FILES:
            from .utils import upload_to_cloudinary
            url = upload_to_cloudinary(request.FILES['screenshot'])
            payment.screenshot_url = url
            payment.save()
        
        # Audit log
        AuditLog.log(
            actor_type='STUDENT',
            actor_id=payment.student.tg_user_id,
            event_type='PAYMENT_UPLOADED',
            payment_id=payment.id,
            amount=str(payment.amount)
        )
        
        # Notify admins
        send_telegram_notification.delay(
            'admin_group',
            f"Payment uploaded by {payment.student.roll_no} for ₹{payment.amount}"
        )
        
        # Sync to sheets
        sync_to_google_sheets.delay('payments', payment.id)
        
        return Response(
            {"message": "Payment uploaded. Awaiting verification."},
            status=status.HTTP_201_CREATED
        )


class PaymentVerificationView(views.APIView):
    """Admin payment verification"""
    
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def post(self, request, payment_id):
        """Verify or deny payment"""
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PaymentVerificationSerializer(
            payment,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        
        # Notify student
        if payment.status == PaymentStatus.VERIFIED:
            message = f"✅ Payment verified for {payment.cycle_start} to {payment.cycle_end}"
        else:
            message = "⚠️ Payment could not be verified. Please re-upload."
        
        send_telegram_notification.delay(payment.student.tg_user_id, message)
        
        # Audit log
        AuditLog.log(
            actor_type='ADMIN',
            actor_id=request.data.get('admin_id'),
            event_type=f'PAYMENT_{payment.status}',
            payment_id=payment.id
        )
        
        # Sync to sheets
        sync_to_google_sheets.delay('payments', payment.id)
        
        return Response({"message": f"Payment {payment.status.lower()}"})


class MessCutView(generics.CreateAPIView):
    """Student mess cut application"""
    
    serializer_class = MessCutSerializer
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Apply for mess cut"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mess_cut = serializer.save(applied_by='STUDENT')
        
        # Check if cutoff was respected
        now = timezone.now()
        tomorrow = (now + timedelta(days=1)).date()
        if mess_cut.from_date <= tomorrow and now.time() <= datetime.strptime('23:00', '%H:%M').time():
            mess_cut.cutoff_ok = True
        else:
            mess_cut.cutoff_ok = False
        mess_cut.save()
        
        # Audit log
        AuditLog.log(
            actor_type='STUDENT',
            actor_id=mess_cut.student.tg_user_id,
            event_type='MESS_CUT_APPLIED',
            mess_cut_id=mess_cut.id,
            dates=f"{mess_cut.from_date} to {mess_cut.to_date}"
        )
        
        # Notify student
        send_telegram_notification.delay(
            mess_cut.student.tg_user_id,
            f"✂️ Mess cut confirmed from {mess_cut.from_date} to {mess_cut.to_date}"
        )
        
        # Sync to sheets
        sync_to_google_sheets.delay('mess_cuts', mess_cut.id)
        
        return Response(
            {"message": "Mess cut applied successfully"},
            status=status.HTTP_201_CREATED
        )


class MessClosureView(generics.CreateAPIView):
    """Admin mess closure declaration"""
    
    serializer_class = MessClosureSerializer
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Declare mess closure"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        closure = serializer.save()
        
        # Audit log
        AuditLog.log(
            actor_type='ADMIN',
            actor_id=closure.created_by_admin_id,
            event_type='MESS_CLOSURE_DECLARED',
            closure_id=closure.id,
            dates=f"{closure.from_date} to {closure.to_date}",
            reason=closure.reason
        )
        
        # Broadcast to all students
        message = f"📢 Mess closed from {closure.from_date} to {closure.to_date}"
        if closure.reason:
            message += f"\nReason: {closure.reason}"
        
        for student in Student.objects.filter(status=StudentStatus.APPROVED):
            send_telegram_notification.delay(student.tg_user_id, message)
        
        # Sync to sheets
        sync_to_google_sheets.delay('mess_closures', closure.id)
        
        return Response(
            {"message": "Mess closure declared and students notified"},
            status=status.HTTP_201_CREATED
        )


class QRScanView(views.APIView):
    """Staff QR scanning endpoint"""
    
    permission_classes = [IsStaff]
    
    @transaction.atomic
    def post(self, request):
        """Process QR scan"""
        serializer = QRScanSerializer(
            data=request.data,
            context={'staff_token': request.auth}
        )
        serializer.is_valid(raise_exception=True)
        
        result = serializer.save()
        
        # Notify student if allowed
        if result['result'] == 'ALLOWED':
            student_id = result['student']['id']
            student = Student.objects.get(id=student_id)
            meal = request.data.get('meal', 'meal')
            
            send_telegram_notification.delay(
                student.tg_user_id,
                f"🍽️ QR scanned at {timezone.now().strftime('%H:%M')} for {meal}"
            )
        
        # Sync to sheets
        sync_to_google_sheets.delay('scan_events', result['scan_event_id'])
        
        return Response(result)


class StudentSnapshotView(generics.RetrieveAPIView):
    """Get student details for staff/admin"""
    
    queryset = Student.objects.all()
    serializer_class = StudentSnapshotSerializer
    permission_classes = [IsStaff]


class BulkQRRegenerateView(views.APIView):
    """Admin bulk QR regeneration"""
    
    permission_classes = [IsAdmin]
    
    @transaction.atomic
    def post(self, request):
        """Regenerate all QR codes"""
        serializer = BulkQRRegenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        admin_id = serializer.validated_data['admin_id']
        
        # Update QR secret version in settings
        from .models import Settings
        settings_obj = Settings.get_settings()
        settings_obj.qr_secret_version += 1
        settings_obj.save()
        
        # Queue regeneration for all approved students
        student_ids = list(
            Student.objects.filter(status=StudentStatus.APPROVED)
            .values_list('id', flat=True)
        )
        
        process_qr_regeneration.delay(student_ids)
        
        # Audit log
        AuditLog.log(
            actor_type='ADMIN',
            actor_id=admin_id,
            event_type='BULK_QR_REGENERATION',
            student_count=len(student_ids)
        )
        
        return Response(
            {"message": f"QR regeneration initiated for {len(student_ids)} students"},
            status=status.HTTP_200_OK
        )


class PaymentReportView(views.APIView):
    """Payment status reports"""
    
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """Get payment report"""
        serializer = ReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        filters = serializer.validated_data
        queryset = Payment.objects.all()
        
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('from_date'):
            queryset = queryset.filter(cycle_start__gte=filters['from_date'])
        
        if filters.get('to_date'):
            queryset = queryset.filter(cycle_end__lte=filters['to_date'])
        
        # Group by status
        report = {
            'verified': queryset.filter(status=PaymentStatus.VERIFIED).count(),
            'pending': queryset.filter(status=PaymentStatus.UPLOADED).count(),
            'denied': queryset.filter(status=PaymentStatus.DENIED).count(),
            'not_uploaded': Student.objects.filter(
                status=StudentStatus.APPROVED
            ).exclude(
                payments__status=PaymentStatus.VERIFIED
            ).count()
        }
        
        return Response(report)


class MessCutReportView(views.APIView):
    """Mess cut reports"""
    
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """Get mess cut report"""
        serializer = ReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        filters = serializer.validated_data
        queryset = MessCut.objects.all()
        
        if filters.get('from_date'):
            queryset = queryset.filter(from_date__gte=filters['from_date'])
        
        if filters.get('to_date'):
            queryset = queryset.filter(to_date__lte=filters['to_date'])
        
        # Group by date
        cuts_by_date = {}
        for cut in queryset:
            date_range = f"{cut.from_date} to {cut.to_date}"
            if date_range not in cuts_by_date:
                cuts_by_date[date_range] = []
            cuts_by_date[date_range].append({
                'student': cut.student.roll_no,
                'name': cut.student.name
            })
        
        return Response(cuts_by_date)