"""
Custom permission classes for API access control
"""

from rest_framework import permissions
from django.conf import settings
import hashlib
import logging

logger = logging.getLogger(__name__)


class IsAdmin(permissions.BasePermission):
    """
    Permission for admin-only endpoints
    Validates against ADMIN_TG_IDS from settings
    """
    
    def has_permission(self, request, view):
        """Check if request has admin privileges"""
        # Check for admin_id in request data
        admin_id = request.data.get('admin_id')
        
        if not admin_id:
            # Try to get from query params
            admin_id = request.query_params.get('admin_id')
        
        if not admin_id:
            # Try to get from headers
            admin_id = request.META.get('HTTP_X_ADMIN_ID')
        
        try:
            admin_id = int(admin_id) if admin_id else None
        except (ValueError, TypeError):
            return False
        
        # Validate against allowed admin IDs
        if admin_id and admin_id in settings.ADMIN_TG_IDS:
            # Log admin action
            logger.info(f"Admin action by {admin_id} on {view.__class__.__name__}")
            return True
        
        logger.warning(f"Unauthorized admin attempt by {admin_id}")
        return False


class IsStaff(permissions.BasePermission):
    """
    Permission for staff scanner endpoints
    Validates staff token
    """
    
    def has_permission(self, request, view):
        """Check if request has valid staff token"""
        from .models import StaffToken
        
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.replace('Bearer ', '').strip()
        
        if not token:
            return False
        
        # Hash the token to compare with database
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            staff_token = StaffToken.objects.get(
                token_hash=token_hash,
                active=True
            )
            
            # Check if token is valid
            if not staff_token.is_valid():
                return False
            
            # Record usage
            staff_token.record_usage()
            
            # Attach token to request for later use
            request.auth = staff_token
            
            return True
            
        except StaffToken.DoesNotExist:
            logger.warning(f"Invalid staff token attempt")
            return False


class IsStudentOwner(permissions.BasePermission):
    """
    Permission to check if student owns the resource
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if student owns the object"""
        # Get student ID from request
        student_tg_id = request.data.get('tg_user_id')
        
        if not student_tg_id:
            student_tg_id = request.query_params.get('tg_user_id')
        
        if not student_tg_id:
            return False
        
        # Check ownership based on object type
        if hasattr(obj, 'student'):
            return obj.student.tg_user_id == int(student_tg_id)
        elif hasattr(obj, 'tg_user_id'):
            return obj.tg_user_id == int(student_tg_id)
        
        return False


class IsTelegramBot(permissions.BasePermission):
    """
    Permission for Telegram bot webhook
    Validates webhook secret
    """
    
    def has_permission(self, request, view):
        """Validate Telegram webhook"""
        # Get secret token from headers
        secret_token = request.META.get('HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN')
        
        if not secret_token:
            return False
        
        # Validate against configured secret
        expected_token = settings.TELEGRAM_WEBHOOK_SECRET
        
        if not expected_token:
            # If no secret configured, allow (development mode)
            logger.warning("No Telegram webhook secret configured")
            return True
        
        return secret_token == expected_token