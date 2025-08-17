"""
Web views for QR Scanner interface using Django templates
Place this file in: mess/scanner_views.py
"""

from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import hashlib
import json
import logging

from .models import StaffToken, Student, ScanEvent
from .serializers import QRScanSerializer, StudentSnapshotSerializer
from .utils import get_current_meal

logger = logging.getLogger(__name__)


class ScannerLoginView(View):
    """Staff login page for scanner access"""
    
    template_name = 'scanner/login.html'
    
    def get(self, request):
        """Display login form"""
        # Check if already authenticated
        if request.session.get('staff_token'):
            return redirect('mess:scanner-main')
        return render(request, self.template_name)
    
    def post(self, request):
        """Process login with token"""
        token = request.POST.get('token', '').strip()
        
        if not token:
            messages.error(request, 'Please enter a token')
            return render(request, self.template_name)
        
        # Validate token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            staff_token = StaffToken.objects.get(
                token_hash=token_hash,
                active=True
            )
            
            if not staff_token.is_valid():
                messages.error(request, 'Token has expired')
                return render(request, self.template_name)
            
            # Store in session
            request.session['staff_token'] = token
            request.session['staff_label'] = staff_token.label
            staff_token.record_usage()
            
            messages.success(request, f'Logged in as {staff_token.label}')
            return redirect('mess:scanner-main')
            
        except StaffToken.DoesNotExist:
            messages.error(request, 'Invalid token')
            return render(request, self.template_name)


class ScannerMainView(TemplateView):
    """Main scanner interface"""
    
    template_name = 'scanner/main.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check authentication"""
        if not request.session.get('staff_token'):
            return redirect('mess:scanner-login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add context data"""
        context = super().get_context_data(**kwargs)
        context['current_meal'] = get_current_meal() or 'LUNCH'
        context['meals'] = ['BREAKFAST', 'LUNCH', 'DINNER']
        context['staff_label'] = self.request.session.get('staff_label', 'Scanner')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class ScannerProcessView(View):
    """Process QR scan via AJAX"""
    
    def dispatch(self, request, *args, **kwargs):
        """Check authentication"""
        if not request.session.get('staff_token'):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        """Process QR scan"""
        try:
            data = json.loads(request.body)
            token = request.session.get('staff_token')
            
            # Get staff token object
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            staff_token = StaffToken.objects.get(token_hash=token_hash)
            
            # Process scan using existing serializer
            serializer = QRScanSerializer(
                data=data,
                context={'staff_token': staff_token}
            )
            
            if serializer.is_valid():
                result = serializer.save()
                
                # Add additional display data
                result['timestamp'] = ScanEvent.objects.filter(
                    id=result['scan_event_id']
                ).first().scanned_at.strftime('%I:%M %p')
                
                return JsonResponse(result)
            else:
                return JsonResponse(
                    {'error': serializer.errors},
                    status=400
                )
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Scan processing error: {e}")
            return JsonResponse(
                {'error': 'Processing failed'},
                status=500
            )


class ScannerLogoutView(View):
    """Logout from scanner"""
    
    def get(self, request):
        """Process logout"""
        request.session.flush()
        messages.success(request, 'Logged out successfully')
        return redirect('mess:scanner-login')


class ScannerStatsView(TemplateView):
    """Scanner statistics page"""
    
    template_name = 'scanner/stats.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check authentication"""
        if not request.session.get('staff_token'):
            return redirect('mess:scanner-login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add statistics"""
        context = super().get_context_data(**kwargs)
        
        from django.utils import timezone
        from django.db.models import Count, Q
        
        today = timezone.now().date()
        
        # Get today's statistics
        scans_today = ScanEvent.objects.filter(
            scanned_at__date=today
        )
        
        context['stats'] = {
            'total_today': scans_today.count(),
            'allowed': scans_today.filter(result='ALLOWED').count(),
            'blocked': scans_today.exclude(result='ALLOWED').count(),
            'breakfast': scans_today.filter(meal='BREAKFAST').count(),
            'lunch': scans_today.filter(meal='LUNCH').count(),
            'dinner': scans_today.filter(meal='DINNER').count(),
        }
        
        # Recent scans
        context['recent_scans'] = scans_today.select_related('student').order_by('-scanned_at')[:10]
        
        return context


class ScannerManualView(TemplateView):
    """Manual entry page for backup"""
    
    template_name = 'scanner/manual.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Check authentication"""
        if not request.session.get('staff_token'):
            return redirect('scanner:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add context"""
        context = super().get_context_data(**kwargs)
        context['current_meal'] = get_current_meal() or 'LUNCH'
        context['meals'] = ['BREAKFAST', 'LUNCH', 'DINNER']
        return context
    
    def post(self, request):
        """Process manual entry"""
        roll_no = request.POST.get('roll_no', '').strip().upper()
        meal = request.POST.get('meal')
        
        try:
            student = Student.objects.get(roll_no=roll_no)
            
            # Generate QR and process
            qr_payload = student.generate_qr_payload(settings.QR_SECRET)
            
            # Process using scanner view
            token = request.session.get('staff_token')
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            staff_token = StaffToken.objects.get(token_hash=token_hash)
            
            serializer = QRScanSerializer(
                data={
                    'qr_data': qr_payload,
                    'meal': meal,
                    'device_info': 'Manual Entry'
                },
                context={'staff_token': staff_token}
            )
            
            if serializer.is_valid():
                result = serializer.save()
                
                if result['result'] == 'ALLOWED':
                    messages.success(request, f"✅ Access granted for {student.name}")
                else:
                    messages.warning(request, f"⚠️ {result['message']}")
            else:
                messages.error(request, 'Processing failed')
                
        except Student.DoesNotExist:
            messages.error(request, f'Student with roll number {roll_no} not found')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('mess:scanner-manual')