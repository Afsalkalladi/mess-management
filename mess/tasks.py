"""
Celery tasks for asynchronous operations
Handles notifications, Google Sheets sync, and background processing
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import requests
import json
import time
from typing import List, Dict, Any, Optional

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def send_telegram_notification(self, recipient, message, attachment=None):
    """
    Send notification via Telegram Bot API
    
    Args:
        recipient: Either tg_user_id or 'admin_group'
        message: Text message to send
        attachment: Optional file/image to attach
    """
    try:
        bot_token = settings.TELEGRAM_BOT_TOKEN
        base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Determine recipient ID
        if recipient == 'admin_group':
            # Send to all admins
            for admin_id in settings.ADMIN_TG_IDS:
                self._send_single_message(base_url, admin_id, message, attachment)
        else:
            self._send_single_message(base_url, recipient, message, attachment)
        
        logger.info(f"Notification sent to {recipient}")
        return True
        
    except Exception as exc:
        logger.error(f"Failed to send notification: {exc}")
        raise self.retry(exc=exc, countdown=60)
    
    def _send_single_message(self, base_url, chat_id, message, attachment):
        """Send message to single recipient"""
        if attachment:
            # Send photo with caption
            url = f"{base_url}/sendPhoto"
            files = {'photo': attachment}
            data = {'chat_id': chat_id, 'caption': message}
            response = requests.post(url, data=data, files=files)
        else:
            # Send text message
            url = f"{base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=data)
        
        response.raise_for_status()


@shared_task(bind=True, max_retries=3)
def sync_to_google_sheets(self, sheet_name: str, record_id: int):
    """
    Sync record to Google Sheets for backup
    
    Args:
        sheet_name: Name of the sheet tab
        record_id: ID of the record to sync
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Initialize Google Sheets API
        credentials = service_account.Credentials.from_service_account_info(
            settings.GOOGLE_SHEETS_CREDENTIALS,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # Get record data
        data = self._get_record_data(sheet_name, record_id)
        if not data:
            logger.warning(f"No data found for {sheet_name}:{record_id}")
            return
        
        # Append to sheet
        body = {'values': [data]}
        result = sheet.values().append(
            spreadsheetId=settings.GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A:Z",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        logger.info(f"Synced {sheet_name}:{record_id} to Google Sheets")
        return True
        
    except Exception as exc:
        logger.error(f"Failed to sync to Google Sheets: {exc}")
        
        # Add to DLQ if max retries exceeded
        if self.request.retries >= self.max_retries:
            from .models import DLQLog
            DLQLog.objects.create(
                operation='sync_to_google_sheets',
                payload={'sheet_name': sheet_name, 'record_id': record_id},
                error_message=str(exc)
            )
        else:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    def _get_record_data(self, sheet_name: str, record_id: int) -> List:
        """Get record data for sheets sync"""
        from .models import Student, Payment, MessCut, MessClosure, ScanEvent
        
        timestamp = timezone.now().isoformat()
        
        if sheet_name == 'registrations':
            obj = Student.objects.get(id=record_id)
            return [
                obj.id, obj.tg_user_id, obj.name, obj.roll_no,
                obj.room_no, obj.phone, obj.status, timestamp
            ]
        
        elif sheet_name == 'payments':
            obj = Payment.objects.get(id=record_id)
            return [
                obj.id, obj.student.roll_no, obj.cycle_start.isoformat(),
                obj.cycle_end.isoformat(), float(obj.amount), obj.status,
                obj.source, timestamp
            ]
        
        elif sheet_name == 'mess_cuts':
            obj = MessCut.objects.get(id=record_id)
            return [
                obj.id, obj.student.roll_no, obj.from_date.isoformat(),
                obj.to_date.isoformat(), obj.applied_by, obj.cutoff_ok,
                timestamp
            ]
        
        elif sheet_name == 'mess_closures':
            obj = MessClosure.objects.get(id=record_id)
            return [
                obj.id, obj.from_date.isoformat(), obj.to_date.isoformat(),
                obj.reason, obj.created_by_admin_id, timestamp
            ]
        
        elif sheet_name == 'scan_events':
            obj = ScanEvent.objects.get(id=record_id)
            return [
                obj.id, obj.student.roll_no, obj.meal, obj.result,
                obj.scanned_at.isoformat(), obj.device_info
            ]
        
        return None


@shared_task
def process_qr_regeneration(student_ids: List[int]):
    """
    Regenerate QR codes for multiple students
    
    Args:
        student_ids: List of student IDs to regenerate QR for
    """
    from .models import Student
    from .utils import generate_qr_code
    
    success_count = 0
    failed_ids = []
    
    for student_id in student_ids:
        try:
            student = Student.objects.get(id=student_id)
            
            # Regenerate QR
            student.regenerate_qr()
            
            # Generate new QR image
            qr_payload = student.generate_qr_payload(settings.QR_SECRET)
            qr_image = generate_qr_code(qr_payload)
            
            # Send to student
            send_telegram_notification.delay(
                student.tg_user_id,
                "🔄 Your QR code has been updated. Here's your new code:",
                attachment=qr_image
            )
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"Failed to regenerate QR for student {student_id}: {e}")
            failed_ids.append(student_id)
    
    logger.info(f"QR regeneration complete: {success_count} success, {len(failed_ids)} failed")
    
    if failed_ids:
        # Retry failed ones
        process_qr_regeneration.apply_async(args=[failed_ids], countdown=300)


@shared_task
def daily_cutoff_enforcement():
    """
    Daily task to enforce mess cut cutoff at 23:00
    Runs at 23:00 IST daily
    """
    from .models import MessCut, Student
    
    tomorrow = (timezone.now() + timedelta(days=1)).date()
    
    # Lock any pending mess cuts for tomorrow
    pending_cuts = MessCut.objects.filter(
        from_date=tomorrow,
        cutoff_ok=True
    )
    
    for cut in pending_cuts:
        # Notify student that their cut is confirmed
        send_telegram_notification.delay(
            cut.student.tg_user_id,
            f"✅ Your mess cut for {tomorrow} is confirmed and locked."
        )
    
    logger.info(f"Daily cutoff enforcement complete. {pending_cuts.count()} cuts locked.")


@shared_task
def process_dlq_retries():
    """
    Process failed operations from Dead Letter Queue
    Runs every hour
    """
    from .models import DLQLog
    
    pending = DLQLog.objects.filter(resolved=False)
    
    for dlq_entry in pending:
        if not dlq_entry.can_retry():
            continue
        
        try:
            # Retry the operation
            if dlq_entry.operation == 'sync_to_google_sheets':
                sync_to_google_sheets.delay(
                    dlq_entry.payload['sheet_name'],
                    dlq_entry.payload['record_id']
                )
                dlq_entry.resolved = True
                dlq_entry.save()
                
        except Exception as e:
            dlq_entry.retry_count += 1
            dlq_entry.last_retry_at = timezone.now()
            dlq_entry.error_message = str(e)
            dlq_entry.save()
            
            logger.error(f"DLQ retry failed for {dlq_entry.id}: {e}")


@shared_task
def generate_daily_reports():
    """
    Generate and send daily reports to admins
    Runs at 6:00 AM IST daily
    """
    from .models import Student, Payment, MessCut, ScanEvent
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Compile statistics
    stats = {
        'date': today.isoformat(),
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
    
    # Format message
    message = f"""
📊 *Daily Report - {today}*

👥 Total Active Students: {stats['total_students']}
⏳ Pending Registrations: {stats['pending_registrations']}
💳 Pending Payment Verifications: {stats['pending_payments']}
✂️ Mess Cuts Today: {stats['mess_cuts_today']}
🍽️ Meals Served Yesterday: {stats['meals_served_yesterday']}
    """
    
    # Send to admins
    send_telegram_notification.delay('admin_group', message)
    
    logger.info(f"Daily report generated for {today}")


@shared_task
def cleanup_old_scan_events():
    """
    Clean up old scan events (keep last 30 days)
    Runs weekly
    """
    from .models import ScanEvent
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Archive to sheets before deletion
    old_events = ScanEvent.objects.filter(scanned_at__lt=cutoff_date)
    
    for event in old_events:
        sync_to_google_sheets.delay('scan_events_archive', event.id)
    
    # Delete old events
    count = old_events.count()
    old_events.delete()
    
    logger.info(f"Cleaned up {count} old scan events")


@shared_task
def validate_payment_cycles():
    """
    Check for expiring payment cycles and notify students
    Runs daily at 9:00 AM IST
    """
    from .models import Student, Payment
    
    # Check payments expiring in 3 days
    warning_date = timezone.now().date() + timedelta(days=3)
    
    expiring_payments = Payment.objects.filter(
        status='VERIFIED',
        cycle_end=warning_date
    ).select_related('student')
    
    for payment in expiring_payments:
        message = f"""
⚠️ *Payment Cycle Expiring Soon*

Your current payment cycle ends on {payment.cycle_end}.
Please upload payment for the next cycle to avoid service interruption.
        """
        send_telegram_notification.delay(payment.student.tg_user_id, message)
    
    logger.info(f"Sent {expiring_payments.count()} payment expiry warnings")