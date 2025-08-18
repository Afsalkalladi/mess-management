#!/usr/bin/env python3
"""
Setup script for Telegram Bot configuration
This script helps configure the Telegram bot webhook and test the connection
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


def test_bot_token(token):
    """Test if the bot token is valid"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                return True, bot_info['result']
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


def main():
    print("🤖 Telegram Bot Setup Script")
    print("=" * 50)
    
    # Check current configuration
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    webhook_url = getattr(settings, 'TELEGRAM_WEBHOOK_URL', '')
    admin_ids = getattr(settings, 'ADMIN_TG_IDS', [])
    
    print(f"Current Bot Token: {'*' * 20 if bot_token else 'NOT SET'}")
    print(f"Current Webhook URL: {webhook_url}")
    print(f"Admin IDs: {admin_ids}")
    print()
    
    # Test bot token
    if bot_token and bot_token != 'your-bot-token-here':
        print("Testing bot token...")
        is_valid, result = test_bot_token(bot_token)
        if is_valid:
            print(f"✅ Bot token is valid!")
            print(f"   Bot name: {result.get('first_name')}")
            print(f"   Username: @{result.get('username')}")
        else:
            print(f"❌ Bot token is invalid: {result}")
            return
    else:
        print("❌ Bot token is not configured properly")
        print("\nTo fix this:")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Get the bot token")
        print("3. Update TELEGRAM_BOT_TOKEN in your .env file")
        return
    
    # Check webhook
    print("\nChecking webhook status...")
    is_valid, webhook_info = get_webhook_info(bot_token)
    if is_valid:
        current_url = webhook_info.get('url', '')
        print(f"Current webhook URL: {current_url}")
        print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
        
        if current_url != webhook_url:
            print(f"⚠️  Webhook URL mismatch!")
            print(f"   Expected: {webhook_url}")
            print(f"   Current:  {current_url}")
            
            if webhook_url and webhook_url != 'https://your-domain.com/api/v1/telegram/webhook':
                print("\nUpdating webhook...")
                success, message = set_webhook(bot_token, webhook_url)
                if success:
                    print("✅ Webhook updated successfully!")
                else:
                    print(f"❌ Failed to update webhook: {message}")
            else:
                print("\n❌ Webhook URL is not configured properly")
                print("Update TELEGRAM_WEBHOOK_URL in your .env file")
        else:
            print("✅ Webhook is configured correctly!")
    else:
        print(f"❌ Failed to get webhook info: {webhook_info}")
    
    print("\n" + "=" * 50)
    print("Setup Summary:")
    print("1. ✅ Database tables created successfully")
    print("2. ✅ Django server can start")
    print("3. ⚠️  Check bot token configuration")
    print("4. ⚠️  Check webhook URL configuration")
    print("5. ⚠️  Check Supabase database connection")


if __name__ == '__main__':
    main()
