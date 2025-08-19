"""
Main URL Configuration for Mess Management System
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Mess app URLs (includes API and Scanner)
    path('', include('mess.urls')),

    # Telegram Mini App
    path('miniapp/', include('mess.miniapp_urls')),
    
    # Health check endpoint
    path('health/', lambda r: JsonResponse({'status': 'ok'}), name='health-check'),
    
    # Root API endpoint
    path('api/', lambda r: JsonResponse({
        'message': 'Mess Management System API',
        'version': '1.0.0',
        'endpoints': {
            'students': '/api/students/',
            'payments': '/api/payments/',
            'scanner': '/api/scanner/',
            'admin': '/api/admin/'
        }
    })),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Error handlers
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'