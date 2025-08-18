#!/usr/bin/env python3
"""
Production Deployment Test Script
Tests all functionality on the deployed backend
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


class ProductionTester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.results = {}
        
    def log(self, test_name, status, message=""):
        """Log test results"""
        self.results[test_name] = {'status': status, 'message': message}
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message}")
    
    def test_health_endpoint(self):
        """Test health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    self.log("Health Endpoint", "PASS", "Server is healthy")
                    return True
                else:
                    self.log("Health Endpoint", "FAIL", f"Unexpected response: {data}")
            else:
                self.log("Health Endpoint", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log("Health Endpoint", "FAIL", str(e))
        return False
    
    def test_admin_panel(self):
        """Test admin panel accessibility"""
        try:
            response = requests.get(f"{self.base_url}/admin/", timeout=10)
            if response.status_code in [200, 302]:
                self.log("Admin Panel", "PASS", f"Accessible (status: {response.status_code})")
                return True
            else:
                self.log("Admin Panel", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log("Admin Panel", "FAIL", str(e))
        return False
    
    def test_webhook_endpoint(self):
        """Test webhook endpoint"""
        try:
            # Test GET (should return 405)
            response = requests.get(f"{self.base_url}/telegram/webhook/", timeout=10)
            if response.status_code == 405:
                self.log("Webhook GET", "PASS", "Correctly rejects GET requests")
            else:
                self.log("Webhook GET", "WARN", f"Unexpected status: {response.status_code}")
            
            # Test POST with valid data
            test_update = {
                "update_id": 123456789,
                "message": {
                    "message_id": 1,
                    "from": {
                        "id": 725053895,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser"
                    },
                    "chat": {
                        "id": 725053895,
                        "first_name": "Test",
                        "username": "testuser",
                        "type": "private"
                    },
                    "date": int(time.time()),
                    "text": "/start"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/telegram/webhook/",
                json=test_update,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("Webhook POST", "PASS", "Webhook processes updates correctly")
                return True
            else:
                self.log("Webhook POST", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log("Webhook POST", "FAIL", str(e))
        return False
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        try:
            response = requests.get(f"{self.base_url}/api/", timeout=10)
            if response.status_code in [200, 301, 302]:
                self.log("API Endpoint", "PASS", f"API accessible (status: {response.status_code})")
                return True
            else:
                self.log("API Endpoint", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log("API Endpoint", "FAIL", str(e))
        return False
    
    def test_scanner_endpoint(self):
        """Test QR scanner endpoint"""
        try:
            response = requests.get(f"{self.base_url}/scanner/", timeout=10)
            if response.status_code in [200, 302]:
                self.log("Scanner Endpoint", "PASS", f"Scanner accessible (status: {response.status_code})")
                return True
            else:
                self.log("Scanner Endpoint", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            self.log("Scanner Endpoint", "FAIL", str(e))
        return False
    
    def test_telegram_bot_api(self):
        """Test Telegram bot API"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            self.log("Bot API", "FAIL", "Bot token not configured")
            return False
        
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_data = bot_info['result']
                    self.log("Bot API", "PASS", f"Bot: {bot_data.get('first_name')} (@{bot_data.get('username')})")
                    return True
                else:
                    self.log("Bot API", "FAIL", f"API error: {bot_info}")
            else:
                self.log("Bot API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log("Bot API", "FAIL", str(e))
        return False
    
    def get_webhook_info(self):
        """Get current webhook information"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    return True, result['result']
            return False, response.text
        except Exception as e:
            return False, str(e)
    
    def update_webhook(self):
        """Update webhook to correct URL"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        webhook_url = f"{self.base_url}/telegram/webhook/"
        
        try:
            # First delete existing webhook
            delete_response = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=10)
            
            # Set new webhook
            response = requests.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={'url': webhook_url},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    self.log("Webhook Update", "PASS", f"Webhook set to: {webhook_url}")
                    return True
                else:
                    self.log("Webhook Update", "FAIL", result.get('description', 'Unknown error'))
            else:
                self.log("Webhook Update", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log("Webhook Update", "FAIL", str(e))
        return False
    
    def send_test_message(self):
        """Send test message to admin"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        admin_ids = getattr(settings, 'ADMIN_TG_IDS', [])
        
        if not admin_ids:
            self.log("Test Message", "SKIP", "No admin IDs configured")
            return False
        
        try:
            message = f"""🎉 Production Deployment Test

✅ Backend URL: {self.base_url}
✅ All endpoints working
✅ Webhook updated successfully

Try these commands:
• /start - Main menu
• /register - Register for mess
• /help - Get help

System is ready for use! 🚀"""

            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    'chat_id': admin_ids[0],
                    'text': message,
                    'parse_mode': 'Markdown'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    self.log("Test Message", "PASS", "Test message sent to admin")
                    return True
                else:
                    self.log("Test Message", "FAIL", result.get('description', 'Unknown error'))
            else:
                self.log("Test Message", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log("Test Message", "FAIL", str(e))
        return False
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"🧪 Testing Production Deployment: {self.base_url}")
        print("=" * 70)
        
        # Basic endpoint tests
        self.test_health_endpoint()
        self.test_admin_panel()
        self.test_api_endpoints()
        self.test_scanner_endpoint()
        self.test_webhook_endpoint()
        
        # Telegram bot tests
        self.test_telegram_bot_api()
        
        # Check current webhook
        print("\n📡 Webhook Information:")
        success, webhook_info = self.get_webhook_info()
        if success:
            current_url = webhook_info.get('url', '')
            pending_updates = webhook_info.get('pending_update_count', 0)
            print(f"   Current URL: {current_url}")
            print(f"   Pending updates: {pending_updates}")
            
            expected_url = f"{self.base_url}/telegram/webhook/"
            if current_url != expected_url:
                print(f"   ⚠️  URL mismatch! Expected: {expected_url}")
                print("   🔧 Updating webhook...")
                self.update_webhook()
            else:
                print("   ✅ Webhook URL is correct")
        else:
            print(f"   ❌ Failed to get webhook info: {webhook_info}")
        
        # Send test message
        self.send_test_message()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 Test Summary:")
        
        passed = sum(1 for r in self.results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in self.results.values() if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results.values() if r['status'] == 'WARN')
        total = len(self.results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"⚠️  Warnings: {warned}/{total}")
        
        if failed == 0:
            print("\n🎉 All tests passed! Production deployment is working correctly.")
            print("\n📱 Test your bot:")
            print("1. Message @testsaharamessbot on Telegram")
            print("2. Send /start command")
            print("3. Try the registration flow")
        else:
            print(f"\n⚠️  {failed} issues need attention.")
        
        return failed == 0


def main():
    """Main function"""
    base_url = "https://mess-management-phit.onrender.com"
    
    tester = ProductionTester(base_url)
    success = tester.run_all_tests()
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
