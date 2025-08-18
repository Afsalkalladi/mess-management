#!/usr/bin/env python3
"""
Comprehensive test script for Mess Management System
Tests all functions including database, Telegram bot, APIs, and services
"""

import os
import sys
import django
import requests
import json
import time
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.db import connection
from django.core.management import call_command
from django.test.client import Client
from django.contrib.auth import get_user_model

User = get_user_model()


class TestRunner:
    def __init__(self):
        self.results = {}
        self.client = Client()
        
    def log(self, test_name, status, message=""):
        """Log test results"""
        self.results[test_name] = {'status': status, 'message': message}
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message}")
    
    def test_database_connection(self):
        """Test database connectivity"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result[0] == 1:
                    db_name = connection.settings_dict['NAME']
                    db_engine = connection.settings_dict['ENGINE']
                    self.log("Database Connection", "PASS", f"Connected to {db_name} ({db_engine})")
                    return True
        except Exception as e:
            self.log("Database Connection", "FAIL", str(e))
            return False
    
    def test_database_tables(self):
        """Test if all required tables exist"""
        try:
            from mess.models import Student, Payment, MessCut, ScanEvent
            
            # Test table existence by doing simple queries
            Student.objects.count()
            Payment.objects.count()
            MessCut.objects.count()
            ScanEvent.objects.count()
            
            self.log("Database Tables", "PASS", "All tables exist and accessible")
            return True
        except Exception as e:
            self.log("Database Tables", "FAIL", str(e))
            return False
    
    def test_telegram_bot_token(self):
        """Test Telegram bot token validity"""
        try:
            token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            if not token or token == 'your-bot-token-here':
                self.log("Telegram Bot Token", "FAIL", "Token not configured")
                return False
            
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_name = bot_info['result'].get('first_name', 'Unknown')
                    bot_username = bot_info['result'].get('username', 'Unknown')
                    self.log("Telegram Bot Token", "PASS", f"Bot: {bot_name} (@{bot_username})")
                    return True
            
            self.log("Telegram Bot Token", "FAIL", f"Invalid token: {response.text}")
            return False
        except Exception as e:
            self.log("Telegram Bot Token", "FAIL", str(e))
            return False
    
    def test_telegram_webhook(self):
        """Test Telegram webhook configuration"""
        try:
            token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            webhook_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', '')
            
            if not webhook_url:
                self.log("Telegram Webhook", "FAIL", "Webhook URL not configured")
                return False
            
            response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10)
            if response.status_code == 200:
                webhook_info = response.json()
                if webhook_info.get('ok'):
                    current_url = webhook_info['result'].get('url', '')
                    pending_updates = webhook_info['result'].get('pending_update_count', 0)
                    
                    if current_url == webhook_url:
                        self.log("Telegram Webhook", "PASS", f"Configured correctly, {pending_updates} pending updates")
                        return True
                    else:
                        self.log("Telegram Webhook", "WARN", f"URL mismatch: expected {webhook_url}, got {current_url}")
                        return False
            
            self.log("Telegram Webhook", "FAIL", f"Failed to get webhook info: {response.text}")
            return False
        except Exception as e:
            self.log("Telegram Webhook", "FAIL", str(e))
            return False
    
    def test_django_server(self):
        """Test Django server endpoints"""
        try:
            # Test health endpoint
            response = self.client.get('/health/')
            if response.status_code in [200, 301, 302]:  # Accept redirects
                self.log("Django Health Endpoint", "PASS", f"Health check working (status: {response.status_code})")
            else:
                self.log("Django Health Endpoint", "FAIL", f"Status: {response.status_code}")
                return False

            # Test API endpoint
            response = self.client.get('/api/')
            if response.status_code in [200, 301, 302]:  # Accept redirects
                self.log("Django API Endpoint", "PASS", f"API endpoint working (status: {response.status_code})")
            else:
                self.log("Django API Endpoint", "FAIL", f"Status: {response.status_code}")
                return False

            # Test admin endpoint
            response = self.client.get('/admin/')
            if response.status_code in [200, 301, 302]:  # 302 is redirect to login
                self.log("Django Admin Endpoint", "PASS", f"Admin panel accessible (status: {response.status_code})")
            else:
                self.log("Django Admin Endpoint", "FAIL", f"Status: {response.status_code}")
                return False

            return True
        except Exception as e:
            self.log("Django Server", "FAIL", str(e))
            return False
    
    def test_telegram_webhook_endpoint(self):
        """Test Telegram webhook endpoint"""
        try:
            response = self.client.post('/telegram/webhook/',
                                      data='{"update_id": 1}',
                                      content_type='application/json')
            # Should return 200 even for invalid data, accept redirects too
            if response.status_code in [200, 301, 302]:
                self.log("Telegram Webhook Endpoint", "PASS", f"Webhook endpoint accessible (status: {response.status_code})")
                return True
            else:
                self.log("Telegram Webhook Endpoint", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log("Telegram Webhook Endpoint", "FAIL", str(e))
            return False
    
    def test_redis_connection(self):
        """Test Redis connection for Celery"""
        try:
            from celery import Celery
            from django.conf import settings
            
            redis_url = getattr(settings, 'CELERY_BROKER_URL', '')
            if not redis_url:
                self.log("Redis Connection", "WARN", "Redis URL not configured")
                return False
            
            # Try to create Celery app and ping Redis
            app = Celery('test')
            app.config_from_object('django.conf:settings', namespace='CELERY')
            
            # Simple test - this will fail if Redis is not accessible
            result = app.control.ping(timeout=5)
            if result:
                self.log("Redis Connection", "PASS", "Redis accessible")
                return True
            else:
                self.log("Redis Connection", "WARN", "Redis not responding")
                return False
        except Exception as e:
            self.log("Redis Connection", "WARN", f"Redis test failed: {str(e)}")
            return False
    
    def test_environment_variables(self):
        """Test critical environment variables"""
        required_vars = [
            'DJANGO_SECRET_KEY',
            'TELEGRAM_BOT_TOKEN',
            'QR_SECRET',
        ]
        
        optional_vars = [
            'CLOUDINARY_URL',
            'GOOGLE_SHEETS_CREDENTIALS_JSON',
            'REDIS_URL',
            'SENTRY_DSN',
        ]
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            value = getattr(settings, var.replace('DJANGO_', ''), None)
            if not value or value in ['your-secret-key-here', 'your-bot-token-here']:
                missing_required.append(var)
        
        for var in optional_vars:
            value = getattr(settings, var.replace('DJANGO_', ''), None)
            if not value:
                missing_optional.append(var)
        
        if missing_required:
            self.log("Environment Variables", "FAIL", f"Missing required: {', '.join(missing_required)}")
            return False
        elif missing_optional:
            self.log("Environment Variables", "WARN", f"Missing optional: {', '.join(missing_optional)}")
            return True
        else:
            self.log("Environment Variables", "PASS", "All variables configured")
            return True
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Running Comprehensive Tests for Mess Management System")
        print("=" * 60)
        
        # Core tests
        self.test_environment_variables()
        self.test_database_connection()
        self.test_database_tables()
        self.test_django_server()
        
        # Telegram tests
        self.test_telegram_bot_token()
        self.test_telegram_webhook()
        self.test_telegram_webhook_endpoint()
        
        # Service tests
        self.test_redis_connection()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        
        passed = sum(1 for r in self.results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in self.results.values() if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results.values() if r['status'] == 'WARN')
        total = len(self.results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"⚠️  Warnings: {warned}/{total}")
        
        if failed == 0:
            print("\n🎉 All critical tests passed! System is ready for deployment.")
        else:
            print(f"\n⚠️  {failed} critical issues need to be fixed before deployment.")
        
        return failed == 0


if __name__ == '__main__':
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
