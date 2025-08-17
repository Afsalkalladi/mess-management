"""
Custom exception handling for the API
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Custom handling for specific exceptions
    if isinstance(exc, ValidationError):
        logger.warning(f"Validation error: {exc}")
        return Response(
            {
                'error': 'Validation Error',
                'message': str(exc),
                'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if isinstance(exc, IntegrityError):
        logger.error(f"Database integrity error: {exc}")
        return Response(
            {
                'error': 'Database Error',
                'message': 'A database constraint was violated. Please check your data.',
                'details': str(exc) if settings.DEBUG else None
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Add custom error data to response
    if response is not None:
        custom_response_data = {
            'error': exc.__class__.__name__,
            'message': str(exc),
            'status_code': response.status_code
        }
        
        # Include original error details in debug mode
        if settings.DEBUG:
            custom_response_data['details'] = response.data
        
        response.data = custom_response_data
        
        # Log the error
        logger.error(
            f"API Error: {exc.__class__.__name__} - {str(exc)}",
            exc_info=True,
            extra={
                'view': context.get('view'),
                'request': context.get('request')
            }
        )
    
    return response


class MessManagementException(Exception):
    """Base exception for Mess Management System"""
    pass


class RegistrationException(MessManagementException):
    """Exception for registration related errors"""
    pass


class PaymentException(MessManagementException):
    """Exception for payment related errors"""
    pass


class QRValidationException(MessManagementException):
    """Exception for QR code validation errors"""
    pass


class CutoffViolationException(MessManagementException):
    """Exception for mess cut cutoff violations"""
    pass