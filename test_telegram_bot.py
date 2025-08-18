#!/usr/bin/env python3
"""
Telegram Bot Testing Script
Tests bot functionality by sending messages and checking responses
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


def send_test_message(chat_id, message):
    """Send a test message to a chat"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return True, "Message sent successfully"
            else:
                return False, result.get('description', 'Unknown error')
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)


def get_bot_updates():
    """Get recent bot updates"""
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return True, result.get('result', [])
            else:
                return False, result.get('description', 'Unknown error')
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)


def test_webhook_endpoint():
    """Test the webhook endpoint with a sample update"""
    from django.test.client import Client
    
    client = Client()
    
    # Sample Telegram update
    sample_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 725053895,  # Admin ID from .env
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
            data=json.dumps(sample_update),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            return True, "Webhook endpoint processed update successfully"
        else:
            return False, f"Webhook returned status {response.status_code}"
    except Exception as e:
        return False, str(e)


def test_database_operations():
    """Test database operations for bot functionality"""
    try:
        from mess.models import Student, Payment, MessCut
        
        # Test creating a student (simulate registration)
        test_student = Student.objects.filter(tg_user_id=999999999).first()
        if not test_student:
            test_student = Student.objects.create(
                tg_user_id=999999999,
                name="Test Student",
                roll_no="TEST001",
                room_no="T001",
                phone="+1234567890",
                status="PENDING"
            )
        
        # Test QR generation
        qr_payload = test_student.generate_qr_payload(settings.QR_SECRET)
        if qr_payload:
            success_msg = f"Database operations working. Test student ID: {test_student.id}"
            
            # Clean up test data
            test_student.delete()
            
            return True, success_msg
        else:
            return False, "QR generation failed"
            
    except Exception as e:
        return False, str(e)


def main():
    """Main testing function"""
    print("🤖 Telegram Bot Functionality Test")
    print("=" * 50)
    
    # Test 1: Bot info
    print("1. Testing bot configuration...")
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    admin_ids = getattr(settings, 'ADMIN_TG_IDS', [])
    
    if not token:
        print("❌ Bot token not configured")
        return False
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_data = bot_info['result']
                print(f"✅ Bot: {bot_data.get('first_name')} (@{bot_data.get('username')})")
                print(f"   Admin IDs: {admin_ids}")
            else:
                print(f"❌ Bot API error: {bot_info}")
                return False
        else:
            print(f"❌ Bot API request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Bot test failed: {e}")
        return False
    
    # Test 2: Webhook endpoint
    print("\n2. Testing webhook endpoint...")
    success, message = test_webhook_endpoint()
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    
    # Test 3: Database operations
    print("\n3. Testing database operations...")
    success, message = test_database_operations()
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
        return False
    
    # Test 4: Send test message to admin (if admin ID is available)
    if admin_ids:
        print(f"\n4. Testing message sending to admin ({admin_ids[0]})...")
        test_message = """🧪 **Test Message from Mess Management Bot**

This is an automated test to verify bot functionality.

✅ Bot is working correctly!
✅ Database connection is active
✅ Webhook endpoint is responding

You can now use the bot with these commands:
• /start - Main menu
• /register - Register for mess
• /payment - Upload payment
• /messcut - Apply for mess cut
• /myqr - View QR code
• /status - Check status"""

        success, message = send_test_message(admin_ids[0], test_message)
        if success:
            print(f"✅ {message}")
            print(f"   Check your Telegram (@{bot_data.get('username')}) for the test message!")
        else:
            print(f"⚠️  Message sending failed: {message}")
            print("   This might be because the admin hasn't started the bot yet.")
    
    # Test 5: Get recent updates
    print("\n5. Checking recent bot activity...")
    success, updates = get_bot_updates()
    if success:
        if updates:
            print(f"✅ Found {len(updates)} recent updates")
            latest_update = updates[-1] if updates else None
            if latest_update and 'message' in latest_update:
                msg = latest_update['message']
                print(f"   Latest: '{msg.get('text', 'N/A')}' from {msg.get('from', {}).get('first_name', 'Unknown')}")
        else:
            print("✅ No recent updates (bot is ready for new messages)")
    else:
        print(f"⚠️  Could not get updates: {updates}")
    
    print("\n" + "=" * 50)
    print("🎉 Telegram Bot Test Completed!")
    print("\nNext steps:")
    print("1. Message the bot on Telegram to test interactively")
    print("2. Try the /start command")
    print("3. Test the registration flow")
    print("4. Deploy to production for full testing")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
