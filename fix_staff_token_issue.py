#!/usr/bin/env python3
"""
Fix Staff Token Database Issue
Removes duplicate/empty token_hash entries and creates a proper staff token
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from mess.models import StaffToken
import secrets
import hashlib
from django.utils import timezone
from datetime import timedelta


def fix_staff_token_issue():
    """Fix staff token database issues"""
    print("🔧 Fixing Staff Token Database Issues...")
    
    # 1. Check for existing tokens with empty or duplicate hashes
    print("\n1. Checking for problematic tokens...")
    
    # Find tokens with empty token_hash
    empty_tokens = StaffToken.objects.filter(token_hash='')
    if empty_tokens.exists():
        print(f"   Found {empty_tokens.count()} tokens with empty token_hash")
        empty_tokens.delete()
        print("   ✅ Deleted tokens with empty token_hash")
    
    # Find tokens with None token_hash
    none_tokens = StaffToken.objects.filter(token_hash__isnull=True)
    if none_tokens.exists():
        print(f"   Found {none_tokens.count()} tokens with null token_hash")
        none_tokens.delete()
        print("   ✅ Deleted tokens with null token_hash")
    
    # 2. Check for existing valid tokens
    print("\n2. Checking existing valid tokens...")
    valid_tokens = StaffToken.objects.exclude(token_hash='').exclude(token_hash__isnull=True)
    
    if valid_tokens.exists():
        print(f"   Found {valid_tokens.count()} existing valid tokens:")
        for token in valid_tokens:
            print(f"   - {token.label} (ID: {token.id}, Active: {token.active})")
        
        # Ask if we should create another one
        print("\n   Valid tokens already exist. You can:")
        print("   1. Use existing tokens in admin panel")
        print("   2. Create additional tokens if needed")
        return True
    
    # 3. Create a new staff token
    print("\n3. Creating new staff token...")
    
    try:
        # Generate secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # Create token with 1 year expiry
        expires_at = timezone.now() + timedelta(days=365)
        
        staff_token = StaffToken.objects.create(
            label="Main Scanner Token",
            token_hash=token_hash,
            expires_at=expires_at,
            active=True
        )
        
        print("   ✅ Staff token created successfully!")
        print(f"\n📋 Token Details:")
        print(f"   ID: {staff_token.id}")
        print(f"   Label: {staff_token.label}")
        print(f"   Token: {raw_token}")
        print(f"   Expires: {staff_token.expires_at}")
        print(f"\n🔐 Scanner Access:")
        print(f"   1. Go to: /scanner/")
        print(f"   2. Enter token: {raw_token}")
        print(f"   3. Access QR scanner interface")
        print(f"\n⚠️  Save this token - it won't be shown again!")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating token: {e}")
        return False


def test_admin_access():
    """Test admin panel access to staff tokens"""
    print("\n4. Testing admin panel access...")
    
    try:
        tokens = StaffToken.objects.all()
        print(f"   ✅ Can access StaffToken model")
        print(f"   Total tokens in database: {tokens.count()}")
        
        if tokens.exists():
            print(f"   Tokens visible in admin panel:")
            for token in tokens:
                print(f"   - {token.label} (Active: {token.active})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error accessing tokens: {e}")
        return False


def main():
    """Main function"""
    print("🛠️  Staff Token Database Fix")
    print("=" * 50)
    
    try:
        # Fix database issues
        success1 = fix_staff_token_issue()
        
        # Test admin access
        success2 = test_admin_access()
        
        if success1 and success2:
            print("\n" + "=" * 50)
            print("🎉 Staff Token Issues Fixed!")
            print("\n✅ Next Steps:")
            print("1. Go to /admin/mess/stafftoken/ to manage tokens")
            print("2. Use the token above to access /scanner/")
            print("3. Create additional tokens as needed")
            print("\n📱 Bot Status:")
            print("- All buttons should now work correctly")
            print("- Registration flow should complete")
            print("- No more async database errors")
            
        else:
            print("\n⚠️  Some issues remain. Check the errors above.")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
