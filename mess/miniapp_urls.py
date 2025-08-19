"""
URL configuration for Telegram Mini App
"""

from django.urls import path
from . import miniapp_views

app_name = 'miniapp'

urlpatterns = [
    # Main Mini App
    path('', miniapp_views.MiniAppView.as_view(), name='index'),
    
    # API endpoints
    path('api/auth/', miniapp_views.MiniAppAuthView.as_view(), name='auth'),
    path('api/student/', miniapp_views.MiniAppStudentView.as_view(), name='student'),
    path('api/payment/', miniapp_views.MiniAppPaymentView.as_view(), name='payment'),
    path('api/qr/', miniapp_views.MiniAppQRView.as_view(), name='qr'),
    path('api/admin/', miniapp_views.MiniAppAdminView.as_view(), name='admin'),
]
