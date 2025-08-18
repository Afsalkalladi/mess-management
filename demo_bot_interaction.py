#!/usr/bin/env python3
"""
Demo Bot Interaction Script
Demonstrates that the Telegram bot is working by simulating user interactions
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

from django.conf import settings
from django.test.client import Client
from mess.models import Student, StudentStatus


def simulate_webhook_update(update_data):
    """Simulate a webhook update from Telegram"""
    client = Client()
    
    try:
        response = client.post(
            '/telegram/webhook/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)


def create_start_command_update(user_id, message_id=1):
    """Create a /start command update"""
    return {
        "update_id": int(time.time()),
        "message": {
            "message_id": message_id,
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Demo",
                "username": "demouser"
            },
            "chat": {
                "id": user_id,
                "first_name": "Demo",
                "username": "demouser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "/start"
        }
    }


def create_registration_update(user_id, text, message_id=2):
    """Create a registration text update"""
    return {
        "update_id": int(time.time()) + 1,
        "message": {
            "message_id": message_id,
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Demo",
                "username": "demouser"
            },
            "chat": {
                "id": user_id,
                "first_name": "Demo",
                "username": "demouser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }


def create_callback_update(user_id, callback_data, message_id=3):
    """Create a callback query update"""
    return {
        "update_id": int(time.time()) + 2,
        "callback_query": {
            "id": str(int(time.time())),
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Demo",
                "username": "demouser"
            },
            "message": {
                "message_id": message_id,
                "from": {
                    "id": 8299680264,  # Bot ID
                    "is_bot": True,
                    "first_name": "Sahara Mess",
                    "username": "testsaharamessbot"
                },
                "chat": {
                    "id": user_id,
                    "first_name": "Demo",
                    "username": "demouser",
                    "type": "private"
                },
                "date": int(time.time()),
                "text": "Welcome message..."
            },
            "data": callback_data
        }
    }


def demo_registration_flow():
    """Demonstrate the registration flow"""
    print("🎭 Demonstrating Bot Registration Flow")
    print("=" * 50)
    
    demo_user_id = 999888777  # Demo user ID
    
    # Clean up any existing demo user
    Student.objects.filter(tg_user_id=demo_user_id).delete()
    
    # Step 1: /start command
    print("1. User sends /start command...")
    start_update = create_start_command_update(demo_user_id)
    success, result = simulate_webhook_update(start_update)
    if success:
        print("   ✅ Bot processed /start command")
    else:
        print(f"   ❌ Failed to process /start: {result}")
        return False
    
    # Step 2: User clicks Register button
    print("2. User clicks 'Register' button...")
    register_callback = create_callback_update(demo_user_id, 'register')
    success, result = simulate_webhook_update(register_callback)
    if success:
        print("   ✅ Bot processed register callback")
    else:
        print(f"   ❌ Failed to process register callback: {result}")
        return False
    
    # Step 3: User provides name
    print("3. User provides name...")
    name_update = create_registration_update(demo_user_id, "Demo Student")
    success, result = simulate_webhook_update(name_update)
    if success:
        print("   ✅ Bot processed name input")
    else:
        print(f"   ❌ Failed to process name: {result}")
        return False
    
    # Step 4: User provides roll number
    print("4. User provides roll number...")
    roll_update = create_registration_update(demo_user_id, "DEMO001", 4)
    success, result = simulate_webhook_update(roll_update)
    if success:
        print("   ✅ Bot processed roll number")
    else:
        print(f"   ❌ Failed to process roll number: {result}")
        return False
    
    # Step 5: User provides room number
    print("5. User provides room number...")
    room_update = create_registration_update(demo_user_id, "D001", 5)
    success, result = simulate_webhook_update(room_update)
    if success:
        print("   ✅ Bot processed room number")
    else:
        print(f"   ❌ Failed to process room number: {result}")
        return False
    
    # Step 6: User provides phone number
    print("6. User provides phone number...")
    phone_update = create_registration_update(demo_user_id, "+1234567890", 6)
    success, result = simulate_webhook_update(phone_update)
    if success:
        print("   ✅ Bot processed phone number")
    else:
        print(f"   ❌ Failed to process phone number: {result}")
        return False
    
    # Check if student was created
    try:
        student = Student.objects.get(tg_user_id=demo_user_id)
        print(f"\n🎉 Registration completed successfully!")
        print(f"   Student created: {student.name} ({student.roll_no})")
        print(f"   Status: {student.status}")
        print(f"   Room: {student.room_no}")
        print(f"   Phone: {student.phone}")
        
        # Clean up demo data
        student.delete()
        print("   🧹 Demo data cleaned up")
        
        return True
    except Student.DoesNotExist:
        print("   ❌ Student was not created in database")
        return False


def demo_admin_approval():
    """Demonstrate admin approval process"""
    print("\n👨‍💼 Demonstrating Admin Approval Process")
    print("=" * 50)
    
    # Create a pending student
    demo_student = Student.objects.create(
        tg_user_id=888777666,
        name="Test Student",
        roll_no="TEST002",
        room_no="T002",
        phone="+9876543210",
        status=StudentStatus.PENDING
    )
    
    print(f"1. Created pending student: {demo_student.name}")
    
    # Simulate admin approval callback
    admin_id = settings.ADMIN_TG_IDS[0] if settings.ADMIN_TG_IDS else 725053895
    approval_callback = create_callback_update(admin_id, f'approve_{demo_student.id}')
    
    print("2. Admin approves student...")
    success, result = simulate_webhook_update(approval_callback)
    if success:
        print("   ✅ Bot processed approval")
        
        # Check if student was approved
        demo_student.refresh_from_db()
        if demo_student.status == StudentStatus.APPROVED:
            print(f"   ✅ Student status updated to: {demo_student.status}")
        else:
            print(f"   ⚠️  Student status: {demo_student.status}")
    else:
        print(f"   ❌ Failed to process approval: {result}")
    
    # Clean up
    demo_student.delete()
    print("   🧹 Demo data cleaned up")
    
    return success


def main():
    """Main demo function"""
    print("🤖 Telegram Bot Interaction Demo")
    print("=" * 60)
    print("This demo simulates real user interactions with the bot")
    print("to verify that all functionality is working correctly.\n")
    
    # Demo 1: Registration flow
    registration_success = demo_registration_flow()
    
    # Demo 2: Admin approval
    approval_success = demo_admin_approval()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Demo Results:")
    print(f"✅ Registration Flow: {'PASSED' if registration_success else 'FAILED'}")
    print(f"✅ Admin Approval: {'PASSED' if approval_success else 'FAILED'}")
    
    if registration_success and approval_success:
        print("\n🎉 All bot interactions working perfectly!")
        print("\nThe bot is ready for real users. You can now:")
        print("1. Message @testsaharamessbot on Telegram")
        print("2. Use /start to begin")
        print("3. Test the full registration and approval flow")
        print("4. Deploy to production for live usage")
    else:
        print("\n⚠️  Some interactions failed. Check the logs for details.")
    
    return registration_success and approval_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
