"""
Telegram Mini App Views for Mess Management System
"""

import json
import hashlib
import hmac
from urllib.parse import unquote, parse_qsl
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.db import transaction

from .models import Student, Payment, StaffToken, ScanEvent, StudentStatus, PaymentStatus
from .serializers import StudentSerializer, PaymentSerializer
from core.utils import generate_qr_code, get_current_meal


def validate_telegram_webapp_data(init_data: str, bot_token: str) -> bool:
    """
    Validate Telegram WebApp init data
    """
    try:
        # Parse the init data
        parsed_data = dict(parse_qsl(init_data))
        
        # Extract hash and remove it from data
        received_hash = parsed_data.pop('hash', '')
        
        # Create data check string
        data_check_arr = []
        for key, value in sorted(parsed_data.items()):
            data_check_arr.append(f"{key}={value}")
        data_check_string = '\n'.join(data_check_arr)
        
        # Create secret key
        secret_key = hmac.new(
            "WebAppData".encode(),
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == received_hash
    except Exception:
        return False


def parse_telegram_user_data(init_data: str) -> dict:
    """
    Parse user data from Telegram WebApp init data
    """
    try:
        parsed_data = dict(parse_qsl(init_data))
        user_data = json.loads(unquote(parsed_data.get('user', '{}')))
        return user_data
    except Exception:
        return {}


class MiniAppView(TemplateView):
    """
    Main Mini App view - serves the React app
    """
    template_name = 'miniapp/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bot_username'] = getattr(settings, 'BOT_USERNAME', 'testsaharamessbot')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class MiniAppAuthView(View):
    """
    Authentication endpoint for Mini App
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            init_data = data.get('initData', '')
            
            # Validate Telegram data
            if not validate_telegram_webapp_data(init_data, settings.TELEGRAM_BOT_TOKEN):
                return JsonResponse({'error': 'Invalid Telegram data'}, status=400)
            
            # Parse user data
            user_data = parse_telegram_user_data(init_data)
            if not user_data:
                return JsonResponse({'error': 'No user data'}, status=400)
            
            # Create session token
            session_token = hashlib.sha256(
                f"{user_data['id']}{timezone.now().timestamp()}".encode()
            ).hexdigest()
            
            # Store in session or cache
            request.session['miniapp_user'] = user_data
            request.session['miniapp_token'] = session_token
            
            return JsonResponse({
                'success': True,
                'token': session_token,
                'user': user_data
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MiniAppStudentView(View):
    """
    Student management for Mini App
    """
    
    def get(self, request):
        """Get student data"""
        user_data = request.session.get('miniapp_user')
        if not user_data:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        try:
            student = Student.objects.get(tg_user_id=user_data['id'])
            serializer = StudentSerializer(student)
            return JsonResponse({
                'success': True,
                'student': serializer.data
            })
        except Student.DoesNotExist:
            return JsonResponse({
                'success': True,
                'student': None
            })
    
    def post(self, request):
        """Register new student"""
        user_data = request.session.get('miniapp_user')
        if not user_data:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        try:
            data = json.loads(request.body)
            
            # Check if already registered
            if Student.objects.filter(tg_user_id=user_data['id']).exists():
                return JsonResponse({'error': 'Already registered'}, status=400)
            
            # Create student
            with transaction.atomic():
                student = Student.objects.create(
                    tg_user_id=user_data['id'],
                    tg_username=user_data.get('username', ''),
                    name=data['name'],
                    roll_no=data['rollNo'],
                    room_no=data['roomNo'],
                    phone=data['phone'],
                    status=StudentStatus.PENDING
                )
            
            serializer = StudentSerializer(student)
            return JsonResponse({
                'success': True,
                'student': serializer.data,
                'message': 'Registration submitted successfully! Please wait for admin approval.'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MiniAppPaymentView(View):
    """
    Payment management for Mini App
    """
    
    def get(self, request):
        """Get payment history"""
        user_data = request.session.get('miniapp_user')
        if not user_data:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        try:
            student = Student.objects.get(tg_user_id=user_data['id'])
            payments = Payment.objects.filter(student=student).order_by('-created_at')
            serializer = PaymentSerializer(payments, many=True)
            
            return JsonResponse({
                'success': True,
                'payments': serializer.data
            })
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Not registered'}, status=400)
    
    def post(self, request):
        """Upload payment"""
        user_data = request.session.get('miniapp_user')
        if not user_data:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        try:
            student = Student.objects.get(tg_user_id=user_data['id'])
            
            if student.status != StudentStatus.APPROVED:
                return JsonResponse({'error': 'Registration not approved'}, status=400)
            
            # Handle file upload
            screenshot = request.FILES.get('screenshot')
            if not screenshot:
                return JsonResponse({'error': 'No screenshot provided'}, status=400)
            
            # Create payment record
            with transaction.atomic():
                payment = Payment.objects.create(
                    student=student,
                    amount=request.POST.get('amount', 0),
                    screenshot=screenshot,
                    status=PaymentStatus.PENDING
                )
            
            serializer = PaymentSerializer(payment)
            return JsonResponse({
                'success': True,
                'payment': serializer.data,
                'message': 'Payment uploaded successfully! Please wait for verification.'
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Not registered'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MiniAppQRView(View):
    """
    QR Code management for Mini App
    """
    
    def get(self, request):
        """Get student QR code"""
        user_data = request.session.get('miniapp_user')
        if not user_data:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        try:
            student = Student.objects.get(tg_user_id=user_data['id'])
            
            if student.status != StudentStatus.APPROVED:
                return JsonResponse({'error': 'Registration not approved'}, status=400)
            
            # Generate QR code
            qr_payload = student.generate_qr_payload(settings.QR_SECRET)
            qr_image_url = generate_qr_code(qr_payload)
            
            return JsonResponse({
                'success': True,
                'qr_code': qr_image_url,
                'student_name': student.name,
                'roll_no': student.roll_no
            })
            
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Not registered'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MiniAppAdminView(View):
    """
    Admin functions for Mini App
    """
    
    def get(self, request):
        """Get admin dashboard data"""
        user_data = request.session.get('miniapp_user')
        if not user_data or user_data['id'] not in settings.ADMIN_TG_IDS:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        try:
            # Get statistics
            total_students = Student.objects.count()
            pending_registrations = Student.objects.filter(status=StudentStatus.PENDING).count()
            approved_students = Student.objects.filter(status=StudentStatus.APPROVED).count()
            pending_payments = Payment.objects.filter(status=PaymentStatus.PENDING).count()
            
            # Get recent registrations
            recent_registrations = Student.objects.filter(
                status=StudentStatus.PENDING
            ).order_by('-created_at')[:5]
            
            return JsonResponse({
                'success': True,
                'stats': {
                    'total_students': total_students,
                    'pending_registrations': pending_registrations,
                    'approved_students': approved_students,
                    'pending_payments': pending_payments
                },
                'recent_registrations': StudentSerializer(recent_registrations, many=True).data
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def post(self, request):
        """Handle admin actions"""
        user_data = request.session.get('miniapp_user')
        if not user_data or user_data['id'] not in settings.ADMIN_TG_IDS:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        try:
            data = json.loads(request.body)
            action = data.get('action')
            student_id = data.get('student_id')
            
            if action in ['approve', 'deny'] and student_id:
                student = Student.objects.get(id=student_id)
                
                if action == 'approve':
                    student.status = StudentStatus.APPROVED
                    message = 'Student approved successfully'
                else:
                    student.status = StudentStatus.DENIED
                    message = 'Student denied'
                
                student.save()
                
                return JsonResponse({
                    'success': True,
                    'message': message
                })
            
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
