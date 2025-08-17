"""
Management command to setup Telegram webhook
Usage: python manage.py setup_telegram_webhook
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'Setup Telegram bot webhook'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--remove',
            action='store_true',
            help='Remove webhook instead of setting it'
        )
    
    def handle(self, *args, **options):
        bot_token = settings.TELEGRAM_BOT_TOKEN
        base_url = f"https://api.telegram.org/bot{bot_token}"
        
        if options['remove']:
            # Remove webhook
            response = requests.post(f"{base_url}/deleteWebhook")
            if response.json().get('ok'):
                self.stdout.write(
                    self.style.SUCCESS('Webhook removed successfully!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed: {response.json()}')
                )
        else:
            # Set webhook
            webhook_url = settings.TELEGRAM_WEBHOOK_URL
            response = requests.post(
                f"{base_url}/setWebhook",
                json={'url': webhook_url}
            )
            
            if response.json().get('ok'):
                self.stdout.write(
                    self.style.SUCCESS(f'Webhook set to: {webhook_url}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed: {response.json()}')
                )
