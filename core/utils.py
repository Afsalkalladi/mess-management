"""
Utility functions for Mess Management System
Helper functions for QR, time, validation, etc.
"""

import hashlib
import hmac
import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, time
from typing import Optional, Tuple, Dict, Any
import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.utils import timezone
import pytz
import logging

logger = logging.getLogger(__name__)


def validate_qr_payload(payload: str, secret: str) -> Tuple[bool, Optional[int]]:
    """
    Validate HMAC-signed QR payload
    
    Args:
        payload: QR code data string
        secret: Secret key for HMAC validation
    
    Returns:
        Tuple of (is_valid, student_id or None)
    """
    try:
        parts = payload.split('|')
        if len(parts) != 5:
            return False, None
        
        version, student_id, qr_version, nonce, signature = parts
        
        # Reconstruct data for verification
        data = f"{version}|{student_id}|{qr_version}|{nonce}"
        expected_signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        if hmac.compare_digest(signature, expected_signature):
            return True, int(student_id)
        
        return False, None
        
    except Exception as e:
        logger.error(f"QR validation error: {e}")
        return False, None


def generate_qr_code(data: str) -> bytes:
    """
    Generate QR code image with branding
    
    Args:
        data: Data to encode in QR
    
    Returns:
        PNG image bytes
    """
    try:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image with logo space
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to PIL Image for manipulation
        img = img.convert('RGB')
        
        # Add text label at bottom
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Add white strip at bottom for text
        new_height = height + 40
        new_img = Image.new('RGB', (width, new_height), 'white')
        new_img.paste(img, (0, 0))
        
        # Add text
        draw = ImageDraw.Draw(new_img)
        text = "Mess Management System"
        
        # Try to use a better font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        # Calculate text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        text_y = height + 10
        
        draw.text((text_x, text_y), text, fill='black', font=font)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        new_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
        
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        raise


def get_current_meal() -> Optional[str]:
    """
    Determine current meal based on time
    
    Returns:
        Meal type (BREAKFAST/LUNCH/DINNER) or None
    """
    tz = pytz.timezone(settings.TIMEZONE)
    current_time = timezone.now().astimezone(tz).time()
    
    meal_timings = settings.MEAL_TIMINGS
    
    for meal, timing in meal_timings.items():
        start = datetime.strptime(timing['start'], '%H:%M').time()
        end = datetime.strptime(timing['end'], '%H:%M').time()
        
        if start <= current_time <= end:
            return meal
    
    return None


def is_within_cutoff_time() -> bool:
    """
    Check if current time is before cutoff (23:00 IST)
    
    Returns:
        True if before cutoff, False otherwise
    """
    tz = pytz.timezone(settings.TIMEZONE)
    current_time = timezone.now().astimezone(tz).time()
    cutoff_time = datetime.strptime(settings.MESS_CUT_CUTOFF_TIME, '%H:%M').time()
    
    return current_time <= cutoff_time


def upload_to_cloudinary(file) -> str:
    """
    Upload file to Cloudinary
    
    Args:
        file: File object to upload
    
    Returns:
        URL of uploaded file
    """
    try:
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        
        # Upload file
        result = cloudinary.uploader.upload(
            file,
            folder="mess_payments",
            resource_type="auto",
            allowed_formats=['jpg', 'jpeg', 'png', 'pdf'],
            max_file_size=10485760  # 10MB
        )
        
        return result['secure_url']
        
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        raise


def calculate_payment_cycle(date: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """
    Calculate payment cycle for given date
    
    Args:
        date: Date to calculate cycle for
    
    Returns:
        Tuple of (cycle_start, cycle_end)
    """
    # Assuming monthly cycles starting on 1st
    import calendar
    
    year = date.year
    month = date.month
    
    cycle_start = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    cycle_end = datetime.date(year, month, last_day)
    
    return cycle_start, cycle_end


def format_telegram_message(template: str, **kwargs) -> str:
    """
    Format message for Telegram with Markdown
    
    Args:
        template: Message template
        **kwargs: Values to substitute
    
    Returns:
        Formatted message
    """
    # Escape special characters for Telegram Markdown
    for key, value in kwargs.items():
        if isinstance(value, str):
            # Escape Markdown special characters
            value = value.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[')
        kwargs[key] = value
    
    return template.format(**kwargs)


def validate_date_range(from_date: datetime.date, to_date: datetime.date) -> bool:
    """
    Validate date range
    
    Args:
        from_date: Start date
        to_date: End date
    
    Returns:
        True if valid, False otherwise
    """
    if from_date > to_date:
        return False
    
    # Check if dates are not too far in future (e.g., max 3 months)
    max_future_date = timezone.now().date() + timezone.timedelta(days=90)
    if to_date > max_future_date:
        return False
    
    return True


def get_student_stats(student_id: int) -> Dict[str, Any]:
    """
    Get comprehensive stats for a student
    
    Args:
        student_id: Student ID
    
    Returns:
        Dictionary with various statistics
    """
    from .models import Student, Payment, MessCut, ScanEvent
    
    try:
        student = Student.objects.get(id=student_id)
        
        # Calculate stats
        total_payments = student.payments.filter(status='VERIFIED').count()
        current_payment = student.payments.filter(
            status='VERIFIED',
            cycle_start__lte=timezone.now().date(),
            cycle_end__gte=timezone.now().date()
        ).first()
        
        total_cuts = student.mess_cuts.count()
        active_cuts = student.mess_cuts.filter(
            from_date__lte=timezone.now().date(),
            to_date__gte=timezone.now().date()
        ).count()
        
        meals_this_month = student.scan_events.filter(
            scanned_at__month=timezone.now().month,
            result='ALLOWED'
        ).count()
        
        return {
            'student_id': student_id,
            'name': student.name,
            'roll_no': student.roll_no,
            'status': student.status,
            'total_payments': total_payments,
            'current_payment_valid': current_payment is not None,
            'total_mess_cuts': total_cuts,
            'active_cuts': active_cuts,
            'meals_this_month': meals_this_month,
            'qr_version': student.qr_version
        }
        
    except Student.DoesNotExist:
        return None


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters
    import re
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Trim to max length
    text = text[:max_length]
    
    # Strip whitespace
    text = text.strip()
    
    return text


def generate_staff_token_url(token: str) -> str:
    """
    Generate scanner URL with staff token
    
    Args:
        token: Staff token
    
    Returns:
        Complete URL for scanner access
    """
    base_url = settings.SCANNER_BASE_URL
    return f"{base_url}/scanner?token={token}"


def parse_telegram_date(date_str: str) -> Optional[datetime.date]:
    """
    Parse date from Telegram input
    
    Args:
        date_str: Date string from Telegram
    
    Returns:
        Parsed date or None
    """
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d.%m.%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None