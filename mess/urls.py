"""
URL configuration for mess app
"""

from django.urls import path
from .views import (
    StudentRegistrationView, StudentApprovalView,
    PaymentUploadView, PaymentVerificationView,
    MessCutView, MessClosureView,
    QRScanView, StudentSnapshotView,
    BulkQRRegenerateView, PaymentReportView, MessCutReportView
)
from .telegram_bot import TelegramWebhookView
from .scanner_views import (
    ScannerLoginView, ScannerMainView, ScannerProcessView,
    ScannerLogoutView, ScannerStatsView, ScannerManualView
)
from core.views import home_view

app_name = 'mess'

urlpatterns = [
    # Home page
    path('', home_view, name='home'),

    # API Endpoints
    # Student endpoints
    path('api/students/register/', StudentRegistrationView.as_view(), name='student-register'),
    path('api/students/<int:student_id>/approve/', StudentApprovalView.as_view(), name='student-approve'),
    path('api/students/<int:student_id>/deny/', StudentApprovalView.as_view(), name='student-deny'),
    path('api/students/<int:pk>/snapshot/', StudentSnapshotView.as_view(), name='student-snapshot'),
    
    # Payment endpoints
    path('api/payments/upload/', PaymentUploadView.as_view(), name='payment-upload'),
    path('api/payments/<int:payment_id>/verify/', PaymentVerificationView.as_view(), name='payment-verify'),
    path('api/payments/<int:payment_id>/deny/', PaymentVerificationView.as_view(), name='payment-deny'),
    
    # Mess operations
    path('api/mess-cuts/', MessCutView.as_view(), name='mess-cut'),
    path('api/mess-closures/', MessClosureView.as_view(), name='mess-closure'),
    
    # Scanner API endpoint
    path('api/scanner/scan/', QRScanView.as_view(), name='api-qr-scan'),
    
    # Admin API endpoints
    path('api/admin/qr/regenerate-all/', BulkQRRegenerateView.as_view(), name='admin-qr-regenerate'),
    path('api/admin/reports/payments/', PaymentReportView.as_view(), name='admin-report-payments'),
    path('api/admin/reports/mess-cuts/', MessCutReportView.as_view(), name='admin-report-cuts'),
    
    # Telegram webhook
    path('telegram/webhook/', TelegramWebhookView.as_view(), name='telegram-webhook'),
    
    # Scanner Web Interface
    path('scanner/', ScannerLoginView.as_view(), name='scanner-login'),
    path('scanner/main/', ScannerMainView.as_view(), name='scanner-main'),
    path('scanner/process/', ScannerProcessView.as_view(), name='scanner-process'),
    path('scanner/logout/', ScannerLogoutView.as_view(), name='scanner-logout'),
    path('scanner/stats/', ScannerStatsView.as_view(), name='scanner-stats'),
    path('scanner/manual/', ScannerManualView.as_view(), name='scanner-manual'),
]