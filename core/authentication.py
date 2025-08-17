"""
Custom authentication classes for the API
"""

from rest_framework import authentication
from rest_framework import exceptions
from django.conf import settings
import hashlib
import logging

logger = logging.getLogger(__name__)


class StaffTokenAuthentication(authentication.BaseAuthentication):
    """
    Token authentication for staff scanner access
    """
    
    keyword = 'Bearer'
    
    def authenticate(self, request):
        """
        Authenticate the request and return a tuple of (user, token)
        """
        auth = authentication.get_authorization_header(request).split()
        
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        
        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)
        
        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = 'Invalid token header. Token string should not contain invalid characters.'
            raise exceptions.AuthenticationFailed(msg)
        
        return self.authenticate_credentials(token)
    
    def authenticate_credentials(self, key):
        """
        Authenticate the token
        """
        # Import here to avoid circular imports
        from mess.models import StaffToken
        
        # Hash the token to compare with database
        token_hash = hashlib.sha256(key.encode()).hexdigest()
        
        try:
            token = StaffToken.objects.get(
                token_hash=token_hash,
                active=True
            )
        except StaffToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')
        
        if not token.is_valid():
            raise exceptions.AuthenticationFailed('Token has expired.')
        
        # Record usage
        token.record_usage()
        
        # Return a tuple of (None, token) since we don't have a User model for staff
        return (None, token)
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response
        """
        return self.keyword


class AdminAuthentication(authentication.BaseAuthentication):
    """
    Authentication for admin endpoints using Telegram ID
    """
    
    def authenticate(self, request):
        """
        Authenticate admin based on Telegram ID
        """
        # Try to get admin_id from various sources
        admin_id = None
        
        # Check request body
        if hasattr(request, 'data'):
            admin_id = request.data.get('admin_id')
        
        # Check query parameters
        if not admin_id:
            admin_id = request.query_params.get('admin_id')
        
        # Check headers
        if not admin_id:
            admin_id = request.META.get('HTTP_X_ADMIN_ID')
        
        if not admin_id:
            return None
        
        try:
            admin_id = int(admin_id)
        except (ValueError, TypeError):
            raise exceptions.AuthenticationFailed('Invalid admin ID format.')
        
        # Validate against allowed admin IDs
        if admin_id not in settings.ADMIN_TG_IDS:
            raise exceptions.AuthenticationFailed('Unauthorized admin ID.')
        
        # Log admin authentication
        logger.info(f"Admin authenticated: {admin_id}")
        
        # Return admin_id as the user
        return (admin_id, None)
    
    def authenticate_header(self, request):
        """
        Return authentication header
        """
        return 'Admin'