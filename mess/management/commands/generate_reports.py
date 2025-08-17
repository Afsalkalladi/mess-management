"""
Management command to generate reports
Usage: python manage.py generate_reports --type daily
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from mess.tasks import generate_daily_reports
from mess.models import Student, Payment, MessCut, ScanEvent
from datetime import timedelta
import csv
import json


class Command(BaseCommand):
    help = 'Generate various reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['daily', 'weekly', 'monthly', 'payments'],
            default='daily',
            help='Type of report to generate'
        )
        parser.add_argument(
            '--output',
            type=str,
            choices=['console', 'csv', 'json'],
            default='console',
            help='Output format'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Output file path for csv/json'
        )
    
    def handle(self, *args, **options):
        report_type = options['type']
        output_format = options['output']
        output_file = options.get('file')
        
        if report_type == 'daily':
            data = self.generate_daily_report()
        elif report_type == 'weekly':
            data = self.generate_weekly_report()
        elif report_type == 'monthly':
            data = self.generate_monthly_report()
        elif report_type == 'payments':
            data = self.generate_payment_report()
        
        self.output_report(data, output_format, output_file)
    
    def generate_daily_report(self):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        return {
            'date': str(today),
            'total_students': Student.objects.filter(status='APPROVED').count(),
            'pending_registrations': Student.objects.filter(status='PENDING').count(),
            'pending_payments': Payment.objects.filter(status='UPLOADED').count(),
            'mess_cuts_today': MessCut.objects.filter(
                from_date__lte=today,
                to_date__gte=today
            ).count(),
            'meals_served_yesterday': ScanEvent.objects.filter(
                scanned_at__date=yesterday,
                result='ALLOWED'
            ).count()
        }
    
    def generate_weekly_report(self):
        # Implement weekly report logic
        pass
    
    def generate_monthly_report(self):
        # Implement monthly report logic
        pass
    
    def generate_payment_report(self):
        # Implement payment report logic
        pass
    
    def output_report(self, data, format, file):
        if format == 'console':
            self.stdout.write(json.dumps(data, indent=2))
        elif format == 'csv' and file:
            with open(file, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=data.keys())
                writer.writeheader()
                writer.writerow(data)
            self.stdout.write(self.style.SUCCESS(f'Report saved to {file}'))
        elif format == 'json' and file:
            with open(file, 'w') as jsonfile:
                json.dump(data, jsonfile, indent=2)
            self.stdout.write(self.style.SUCCESS(f'Report saved to {file}'))