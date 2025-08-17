"""
Django app configuration for Mess Management System
"""

from django.apps import AppConfig


class MessConfig(AppConfig):
    """Configuration for the mess app"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mess'
    verbose_name = 'Mess Management'
    
    def ready(self):
        """
        Initialize app when Django starts
        """
        # Import signal handlers if any
        try:
            from . import signals
        except ImportError:
            pass
        
        # Initialize Telegram bot
        from django.conf import settings
        if hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
            from .telegram_bot import TelegramBot
            # Bot will be initialized when needed
            pass


class CoreConfig(AppConfig):
    """Configuration for the core app"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core Utilities'