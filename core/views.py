"""
Core views and error handlers
"""

from django.shortcuts import render
from django.http import JsonResponse


def home_view(request):
    """Home page view"""
    return render(request, 'home.html')


def error_404(request, exception):
    """Custom 404 error handler"""
    if request.path.startswith('/api/'):
        return JsonResponse(
            {'error': 'Not Found', 'message': 'The requested resource was not found'},
            status=404
        )
    return render(request, '404.html', status=404)


def error_500(request):
    """Custom 500 error handler"""
    if request.path.startswith('/api/'):
        return JsonResponse(
            {'error': 'Internal Server Error', 'message': 'An error occurred processing your request'},
            status=500
        )
    return render(request, '500.html', status=500)