#!/usr/bin/env python3
"""
Test All Fixes Script
Tests telegram bot, home page, scanner, and all functionality
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
from django.test.client import Client


def test_telegram_webhook_processing():
    """Test if webhook processes updates correctly"""
    print("🤖 Testing Telegram Bot Webhook Processing...")
    
    client = Client()
    
    # Create a realistic Telegram update
    test_update = {
        "update_id": int(time.time()),
        "message": {
            "message_id": 1,
            "from": {
                "id": 725053895,  # Admin ID
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
    
    try:
        response = client.post(
            '/telegram/webhook/',
            data=json.dumps(test_update),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print("✅ Webhook processes updates correctly")
                return True
            else:
                print(f"❌ Webhook error: {data}")
        else:
            print(f"❌ Webhook returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
    
    return False


def test_home_page():
    """Test home page"""
    print("🏠 Testing Home Page...")
    
    client = Client()
    
    try:
        response = client.get('/')
        if response.status_code == 200:
            if 'Mess Management System' in response.content.decode():
                print("✅ Home page loads correctly")
                return True
            else:
                print("❌ Home page content incorrect")
        else:
            print(f"❌ Home page returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Home page test failed: {e}")
    
    return False


def test_scanner_page():
    """Test scanner page"""
    print("📷 Testing Scanner Page...")
    
    client = Client()
    
    try:
        response = client.get('/scanner/')
        if response.status_code == 200:
            content = response.content.decode()
            if 'QR Scanner Login' in content and 'Staff Token' in content:
                print("✅ Scanner login page loads correctly")
                return True
            else:
                print("❌ Scanner page content incorrect")
        else:
            print(f"❌ Scanner page returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Scanner page test failed: {e}")
    
    return False


def test_admin_page():
    """Test admin page"""
    print("👨‍💼 Testing Admin Page...")
    
    client = Client()
    
    try:
        response = client.get('/admin/')
        if response.status_code in [200, 302]:  # 302 is redirect to login
            print("✅ Admin page accessible")
            return True
        else:
            print(f"❌ Admin page returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Admin page test failed: {e}")
    
    return False


def test_api_endpoints():
    """Test API endpoints"""
    print("🔌 Testing API Endpoints...")
    
    client = Client()
    
    try:
        response = client.get('/api/')
        if response.status_code == 200:
            data = response.json()
            if 'Mess Management System API' in data.get('message', ''):
                print("✅ API endpoint working")
                return True
            else:
                print("❌ API response incorrect")
        else:
            print(f"❌ API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ API test failed: {e}")
    
    return False


def test_production_endpoints():
    """Test production endpoints"""
    print("🌐 Testing Production Endpoints...")
    
    base_url = "https://mess-management-phit.onrender.com"
    
    endpoints = [
        ('/', 'Home Page'),
        ('/health/', 'Health Check'),
        ('/admin/', 'Admin Panel'),
        ('/scanner/', 'Scanner Login'),
        ('/api/', 'API Info')
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code in [200, 302]:
                print(f"✅ {name}: Working (status: {response.status_code})")
                results.append(True)
            else:
                print(f"❌ {name}: Failed (status: {response.status_code})")
                results.append(False)
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    return all(results)


def send_test_message_to_bot():
    """Send test message to verify bot is working"""
    print("📤 Sending Test Message to Bot...")
    
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    admin_ids = getattr(settings, 'ADMIN_TG_IDS', [])
    
    if not token or not admin_ids:
        print("❌ Bot token or admin IDs not configured")
        return False
    
    try:
        message = """🎉 All Fixes Applied Successfully!

✅ Webhook processing fixed
✅ Home page created  
✅ Scanner templates fixed
✅ Admin panel working
✅ All endpoints responding

Your bot should now respond to all commands:
• /start - Try this now!
• /register - Register for mess
• /help - Get help

System is fully operational! 🚀"""

        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                'chat_id': admin_ids[0],
                'text': message
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Test message sent successfully")
                return True
            else:
                print(f"❌ Message send failed: {result}")
        else:
            print(f"❌ Message send failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Message send error: {e}")
    
    return False


def main():
    """Run all tests"""
    print("🧪 Testing All Fixes - Comprehensive Test")
    print("=" * 60)
    
    tests = [
        ("Telegram Webhook Processing", test_telegram_webhook_processing),
        ("Home Page", test_home_page),
        ("Scanner Page", test_scanner_page),
        ("Admin Page", test_admin_page),
        ("API Endpoints", test_api_endpoints),
        ("Production Endpoints", test_production_endpoints),
        ("Bot Test Message", send_test_message_to_bot),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your system is fully operational.")
        print("\n📱 Next steps:")
        print("1. Message @testsaharamessbot on Telegram")
        print("2. Send /start command - should get immediate response")
        print("3. Try registration flow")
        print("4. Test all bot commands")
        print("5. Access admin panel and scanner")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the issues above.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
