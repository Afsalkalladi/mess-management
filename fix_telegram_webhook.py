#!/usr/bin/env python3
"""
Fix Telegram Webhook Script
Updates the webhook URL and tests bot functionality
"""

import os
import sys
import django
import requests
import json
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings


def delete_webhook(token):
    """Delete current webhook"""
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=10)
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False), result.get('description', 'Unknown error')
        return False, response.text
    except Exception as e:
        return False, str(e)


def set_webhook(token, webhook_url):
    """Set the webhook for the bot"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={'url': webhook_url},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False), result.get('description', 'Unknown error')
        return False, response.text
    except Exception as e:
        return False, str(e)


def get_webhook_info(token):
    """Get current webhook information"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return True, result['result']
        return False, response.text
    except Exception as e:
        return False, str(e)


def test_webhook_endpoint(webhook_url):
    """Test if webhook endpoint is accessible"""
    try:
        # Remove the webhook part and test the base URL
        base_url = webhook_url.replace('/telegram/webhook/', '/health/')
        response = requests.get(base_url, timeout=10)
        return response.status_code in [200, 301, 302], response.status_code
    except Exception as e:
        return False, str(e)


def send_test_message(token, chat_id):
    """Send a test message"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                'chat_id': chat_id,
                'text': '🔧 Webhook fixed! Bot is now responding correctly.\n\nTry these commands:\n• /start - Main menu\n• /register - Register for mess\n• /help - Get help'
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False), result.get('description', 'Message sent')
        return False, response.text
    except Exception as e:
        return False, str(e)


def main():
    """Main function to fix webhook"""
    print("🔧 Fixing Telegram Bot Webhook")
    print("=" * 50)
    
    # Get configuration
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    webhook_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', '')
    admin_ids = getattr(settings, 'ADMIN_TG_IDS', [])
    
    if not token:
        print("❌ Bot token not configured")
        return False
    
    if not webhook_url:
        print("❌ Webhook URL not configured")
        return False
    
    print(f"Bot Token: {'*' * 20}")
    print(f"Webhook URL: {webhook_url}")
    print(f"Admin IDs: {admin_ids}")
    
    # Test webhook endpoint accessibility
    print("\n1. Testing webhook endpoint accessibility...")
    accessible, status = test_webhook_endpoint(webhook_url)
    if accessible:
        print(f"✅ Webhook endpoint accessible (status: {status})")
    else:
        print(f"⚠️  Webhook endpoint issue (status: {status})")
    
    # Get current webhook info
    print("\n2. Getting current webhook info...")
    success, webhook_info = get_webhook_info(token)
    if success:
        current_url = webhook_info.get('url', '')
        pending_updates = webhook_info.get('pending_update_count', 0)
        print(f"Current webhook: {current_url}")
        print(f"Pending updates: {pending_updates}")
        
        if pending_updates > 0:
            print(f"⚠️  {pending_updates} pending updates - webhook may not be working properly")
    else:
        print(f"❌ Failed to get webhook info: {webhook_info}")
    
    # Delete current webhook
    print("\n3. Deleting current webhook...")
    success, message = delete_webhook(token)
    if success:
        print(f"✅ Webhook deleted: {message}")
    else:
        print(f"⚠️  Webhook deletion failed: {message}")
    
    # Set new webhook
    print("\n4. Setting new webhook...")
    success, message = set_webhook(token, webhook_url)
    if success:
        print(f"✅ Webhook set successfully: {message}")
    else:
        print(f"❌ Failed to set webhook: {message}")
        return False
    
    # Verify new webhook
    print("\n5. Verifying new webhook...")
    success, webhook_info = get_webhook_info(token)
    if success:
        current_url = webhook_info.get('url', '')
        pending_updates = webhook_info.get('pending_update_count', 0)
        print(f"✅ New webhook URL: {current_url}")
        print(f"✅ Pending updates: {pending_updates}")
        
        if current_url == webhook_url:
            print("✅ Webhook URL matches configuration")
        else:
            print(f"⚠️  Webhook URL mismatch!")
    else:
        print(f"❌ Failed to verify webhook: {webhook_info}")
    
    # Send test message to admin
    if admin_ids:
        print(f"\n6. Sending test message to admin ({admin_ids[0]})...")
        success, message = send_test_message(token, admin_ids[0])
        if success:
            print(f"✅ Test message sent successfully")
        else:
            print(f"⚠️  Test message failed: {message}")
    
    print("\n" + "=" * 50)
    print("🎉 Webhook Fix Completed!")
    print("\nNext steps:")
    print("1. Test the bot by messaging @testsaharamessbot")
    print("2. Try the /start command")
    print("3. Test registration flow")
    print("4. Monitor for any webhook errors")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
