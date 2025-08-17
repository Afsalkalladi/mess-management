"""
Celery configuration for Mess Management System
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('mess_management')

# Configure from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks
app.autodiscover_tasks()

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    # Daily cutoff enforcement at 11:00 PM IST
    'daily-cutoff-enforcement': {
        'task': 'mess.tasks.daily_cutoff_enforcement',
        'schedule': crontab(hour=23, minute=0),
        'options': {
            'timezone': 'Asia/Kolkata'
        }
    },
    
    # Daily reports at 6:00 AM IST
    'daily-reports': {
        'task': 'mess.tasks.generate_daily_reports',
        'schedule': crontab(hour=6, minute=0),
        'options': {
            'timezone': 'Asia/Kolkata'
        }
    },
    
    # Payment cycle validation at 9:00 AM IST
    'payment-validation': {
        'task': 'mess.tasks.validate_payment_cycles',
        'schedule': crontab(hour=9, minute=0),
        'options': {
            'timezone': 'Asia/Kolkata'
        }
    },
    
    # DLQ retry processing every hour
    'dlq-retry': {
        'task': 'mess.tasks.process_dlq_retries',
        'schedule': crontab(minute=0),
    },
    
    # Weekly cleanup on Sunday at 2:00 AM IST
    'weekly-cleanup': {
        'task': 'mess.tasks.cleanup_old_scan_events',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),
        'options': {
            'timezone': 'Asia/Kolkata'
        }
    },
}

# Task routing
app.conf.task_routes = {
    'mess.tasks.send_telegram_notification': {'queue': 'notifications'},
    'mess.tasks.sync_to_google_sheets': {'queue': 'sheets'},
    'mess.tasks.process_qr_regeneration': {'queue': 'qr'},
    'mess.tasks.*': {'queue': 'default'},
}

# Task time limits
app.conf.task_time_limit = 300  # 5 minutes
app.conf.task_soft_time_limit = 240  # 4 minutes

# Result backend configuration
app.conf.result_expires = 3600  # 1 hour

# Worker configuration
app.conf.worker_prefetch_multiplier = 4
app.conf.worker_max_tasks_per_child = 100

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')