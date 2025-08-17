"""
URL configuration for Mess Management System
API v1 endpoints with proper versioning
"""

from django.urls import path, include
from django.contrib import admin
from .views import (
    StudentRegistrationView, StudentApprovalView,
    PaymentUploadView, PaymentVerificationView,
    MessCutView, MessClosureView,
    QRScanView, StudentSnapshotView,
    BulkQRRegenerateView, PaymentReportView, MessCutReportView
)
from .telegram_bot import TelegramWebhookView

app_name = 'mess'

# API v1 patterns
api_v1_patterns = [
    # Student endpoints
    path('students/register/', StudentRegistrationView.as_view(), name='student-register'),
    path('students/<int:student_id>/approve/', 
         StudentApprovalView.as_view(), name='student-approve'),
    path('students/<int:student_id>/deny/', 
         StudentApprovalView.as_view(), name='student-deny'),
    path('students/<int:pk>/snapshot/', 
         StudentSnapshotView.as_view(), name='student-snapshot'),
    
    # Payment endpoints
    path('payments/upload/', PaymentUploadView.as_view(), name='payment-upload'),
    path('payments/<int:payment_id>/verify/', 
         PaymentVerificationView.as_view(), name='payment-verify'),
    path('payments/<int:payment_id>/deny/', 
         PaymentVerificationView.as_view(), name='payment-deny'),
    
    # Mess operations
    path('mess-cuts/', MessCutView.as_view(), name='mess-cut'),
    path('mess-closures/', MessClosureView.as_view(), name='mess-closure'),
    
    # Scanner endpoints
    path('scanner/scan/', QRScanView.as_view(), name='qr-scan'),
    
    # Admin endpoints
    path('admin/registrations/<int:student_id>/<str:action>/', 
         StudentApprovalView.as_view(), name='admin-registration'),
    path('admin/payments/<int:payment_id>/verify/', 
         PaymentVerificationView.as_view(), name='admin-payment-verify'),
    path('admin/payments/<int:payment_id>/deny/', 
         PaymentVerificationView.as_view(), name='admin-payment-deny'),
    path('admin/qr/regenerate-all/', 
         BulkQRRegenerateView.as_view(), name='admin-qr-regenerate'),
    path('admin/reports/payments/', 
         PaymentReportView.as_view(), name='admin-report-payments'),
    path('admin/reports/mess-cuts/', 
         MessCutReportView.as_view(), name='admin-report-cuts'),
    
    # Telegram webhook
    path('telegram/webhook/', TelegramWebhookView.as_view(), name='telegram-webhook'),
]

# Main URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(api_v1_patterns)),
    path('health/', lambda r: JsonResponse({'status': 'ok'}), name='health-check'),
]

# Error handlers
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'