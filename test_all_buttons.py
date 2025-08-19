#!/usr/bin/env python3
"""
Test All Bot Buttons
Tests all callback handlers to ensure they work correctly
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


def create_callback_update(callback_data, user_id=725053895):
    """Create a callback query update"""
    return {
        "update_id": int(time.time()),
        "callback_query": {
            "id": str(int(time.time())),
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "message": {
                "message_id": 1,
                "from": {
                    "id": 8299680264,
                    "is_bot": True,
                    "first_name": "Sahara Mess",
                    "username": "testsaharamessbot"
                },
                "chat": {
                    "id": user_id,
                    "first_name": "Test",
                    "username": "testuser",
                    "type": "private"
                },
                "date": int(time.time()),
                "text": "Welcome message...",
                "reply_markup": {"inline_keyboard": []}
            },
            "chat_instance": str(int(time.time())),
            "data": callback_data
        }
    }


def test_button_callback(button_name, callback_data, user_id=725053895):
    """Test a specific button callback"""
    print(f"🔘 Testing {button_name} button...")
    
    client = Client()
    
    # Create callback update
    test_update = create_callback_update(callback_data, user_id)
    
    try:
        response = client.post(
            '/telegram/webhook/',
            data=json.dumps(test_update),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"   ✅ {button_name} button works correctly")
                return True
            else:
                print(f"   ❌ {button_name} button error: {data}")
        else:
            print(f"   ❌ {button_name} button failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ {button_name} button exception: {e}")
    
    return False


def test_all_buttons():
    """Test all bot buttons"""
    print("🧪 Testing All Bot Buttons")
    print("=" * 50)
    
    # Test buttons with regular user
    regular_user_tests = [
        ("Register", "register"),
        ("Payment", "payment"),
        ("Mess Cut", "messcut"),
        ("My QR", "myqr"),
        ("Help", "help"),
    ]
    
    # Test buttons with admin user (admin ID from settings)
    admin_user_tests = [
        ("Admin Panel", "admin"),
        ("Back to Main", "back_to_main"),
    ]
    
    results = []
    
    print("\n📱 Testing Regular User Buttons:")
    for button_name, callback_data in regular_user_tests:
        result = test_button_callback(button_name, callback_data, user_id=123456789)
        results.append(result)
    
    print("\n👨‍💼 Testing Admin User Buttons:")
    for button_name, callback_data in admin_user_tests:
        result = test_button_callback(button_name, callback_data, user_id=725053895)  # Admin ID
        results.append(result)
    
    # Test admin panel sub-buttons
    print("\n🔧 Testing Admin Panel Sub-buttons:")
    admin_sub_tests = [
        ("Admin Registrations", "admin_registrations"),
        ("Admin Payments", "admin_payments"),
        ("Admin Stats", "admin_stats"),
        ("Admin Settings", "admin_settings"),
    ]
    
    for button_name, callback_data in admin_sub_tests:
        result = test_button_callback(button_name, callback_data, user_id=725053895)
        results.append(result)
    
    return results


def test_staff_token_creation():
    """Test staff token creation in admin panel"""
    print("\n🔑 Testing Staff Token Creation...")
    
    try:
        from mess.models import StaffToken
        
        # Check if we can create a token programmatically
        import secrets
        import hashlib
        from django.utils import timezone
        from datetime import timedelta
        
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = timezone.now() + timedelta(days=30)
        
        staff_token = StaffToken.objects.create(
            label="Test Token",
            token_hash=token_hash,
            expires_at=expires_at,
            active=True
        )
        
        print(f"   ✅ Staff token created successfully (ID: {staff_token.id})")
        print(f"   Token: {token}")
        
        # Clean up test token
        staff_token.delete()
        print(f"   ✅ Test token cleaned up")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Staff token creation failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Comprehensive Bot Button Test")
    print("=" * 60)
    
    # Test all buttons
    button_results = test_all_buttons()
    
    # Test staff token creation
    token_result = test_staff_token_creation()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = sum(button_results) + (1 if token_result else 0)
    total = len(button_results) + 1
    
    print(f"\n✅ Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n📱 Your bot is fully functional:")
        print("   • All buttons respond correctly")
        print("   • Admin panel works")
        print("   • Staff tokens can be created")
        print("   • Registration flow works")
        print("\n🚀 Ready for production use!")
    else:
        failed = total - passed
        print(f"\n⚠️  {failed} tests failed.")
        print("Check the error messages above for details.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
