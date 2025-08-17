# mess/management/commands/create_staff_token.py
"""
Management command to create staff tokens
Usage: python manage.py create_staff_token "Scanner Device 1"
"""

from django.core.management.base import BaseCommand
from mess.models import StaffToken
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Create a new staff token for scanner access'
    
    def add_arguments(self, parser):
        parser.add_argument('label', type=str, help='Label for the token')
        parser.add_argument(
            '--expires',
            type=int,
            default=None,
            help='Token expiry in days (optional)'
        )
    
    def handle(self, *args, **options):
        label = options['label']
        expires_days = options.get('expires')
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        token, instance = StaffToken.create_token(label, expires_at)
        
        self.stdout.write(
            self.style.SUCCESS(f'Token created successfully!\n')
        )
        self.stdout.write(f'Label: {label}\n')
        self.stdout.write(f'Token: {token}\n')
        self.stdout.write(f'Expires: {expires_at or "Never"}\n')
        self.stdout.write(
            self.style.WARNING('\nKeep this token secure! It cannot be retrieved again.')
        )
