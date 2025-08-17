"""
Management command to initialize system settings
Usage: python manage.py initialize_settings
"""

from django.core.management.base import BaseCommand
from mess.models import Settings
import json


class Command(BaseCommand):
    help = 'Initialize system settings with defaults'
    
    def handle(self, *args, **options):
        settings, created = Settings.objects.get_or_create(
            pk=1,
            defaults={
                'tz': 'Asia/Kolkata',
                'cutoff_time': '23:00',
                'qr_secret_version': 1,
                'qr_secret_hash': '',
                'meals': {
                    'BREAKFAST': {'start': '07:00', 'end': '09:30'},
                    'LUNCH': {'start': '12:00', 'end': '14:30'},
                    'DINNER': {'start': '19:00', 'end': '21:30'}
                }
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Settings initialized successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Settings already exist.')
            )