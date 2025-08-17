"""
URL configuration for scanner web interface
"""

from django.urls import path
from .scanner_views import (
    ScannerLoginView,
    ScannerMainView,
    ScannerProcessView,
    ScannerLogoutView,
    ScannerStatsView,
    ScannerManualView
)

app_name = 'scanner'

urlpatterns = [
    # Scanner web interface
    path('', ScannerLoginView.as_view(), name='login'),
    path('scanner/', ScannerMainView.as_view(), name='main'),
    path('scanner/process/', ScannerProcessView.as_view(), name='process'),
    path('scanner/logout/', ScannerLogoutView.as_view(), name='logout'),
    path('scanner/stats/', ScannerStatsView.as_view(), name='stats'),
    path('scanner/manual/', ScannerManualView.as_view(), name='manual'),
]