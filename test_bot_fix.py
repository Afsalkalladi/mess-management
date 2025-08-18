#!/usr/bin/env python3
"""
Test Bot Fix Script
Tests the fixed webhook processing
"""

import os
import sys
import django
import json
import time
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test.client import Client


def test_webhook_with_start_command():
    """Test webhook with /start command"""
    print("🤖 Testing Webhook with /start Command...")
    
    client = Client()
    
    # Create a realistic /start update
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
            "text": "/start",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}]
        }
    }
    
    try:
        print("Sending /start command to webhook...")
        response = client.post(
            '/telegram/webhook/',
            data=json.dumps(test_update),
            content_type='application/json'
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {data}")
            
            if data.get('ok'):
                print("✅ Webhook processed /start command successfully!")
                print("   The bot should have sent a response message.")
                return True
            else:
                print(f"❌ Webhook returned error: {data}")
        else:
            print(f"❌ Webhook returned status {response.status_code}")
            print(f"Response: {response.content.decode()}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    return False


def test_webhook_with_register_command():
    """Test webhook with /register command"""
    print("\n📝 Testing Webhook with /register Command...")
    
    client = Client()
    
    # Create a /register update
    test_update = {
        "update_id": int(time.time()) + 1,
        "message": {
            "message_id": 2,
            "from": {
                "id": 123456789,  # Different user
                "is_bot": False,
                "first_name": "Student",
                "username": "student123"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Student",
                "username": "student123",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "/register",
            "entities": [{"offset": 0, "length": 9, "type": "bot_command"}]
        }
    }
    
    try:
        print("Sending /register command to webhook...")
        response = client.post(
            '/telegram/webhook/',
            data=json.dumps(test_update),
            content_type='application/json'
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {data}")
            
            if data.get('ok'):
                print("✅ Webhook processed /register command successfully!")
                return True
            else:
                print(f"❌ Webhook returned error: {data}")
        else:
            print(f"❌ Webhook returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    return False


def test_webhook_with_text_message():
    """Test webhook with regular text message"""
    print("\n💬 Testing Webhook with Text Message...")
    
    client = Client()
    
    # Create a text message update
    test_update = {
        "update_id": int(time.time()) + 2,
        "message": {
            "message_id": 3,
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
            "text": "Hello bot!"
        }
    }
    
    try:
        print("Sending text message to webhook...")
        response = client.post(
            '/telegram/webhook/',
            data=json.dumps(test_update),
            content_type='application/json'
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {data}")
            
            if data.get('ok'):
                print("✅ Webhook processed text message successfully!")
                return True
            else:
                print(f"❌ Webhook returned error: {data}")
        else:
            print(f"❌ Webhook returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    return False


def main():
    """Run all webhook tests"""
    print("🧪 Testing Fixed Telegram Bot Webhook")
    print("=" * 50)
    
    tests = [
        ("Start Command", test_webhook_with_start_command),
        ("Register Command", test_webhook_with_register_command), 
        ("Text Message", test_webhook_with_text_message),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All webhook tests passed!")
        print("\n📱 Your bot should now respond to:")
        print("1. /start command - Main menu")
        print("2. /register command - Registration flow")
        print("3. Text messages - Appropriate responses")
        print("\nDeploy the fix and test with real Telegram messages!")
    else:
        print(f"\n⚠️  {total - passed} tests failed.")
        print("Check the error messages above for details.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
