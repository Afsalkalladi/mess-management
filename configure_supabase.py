#!/usr/bin/env python3
"""
Supabase Configuration Script
Helps configure Supabase database connection with host/port format
"""

import os
import sys
import re
from pathlib import Path


def parse_database_url(url):
    """Parse DATABASE_URL into components"""
    # Pattern: postgresql://user:password@host:port/database
    pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
    match = re.match(pattern, url)
    
    if match:
        return {
            'user': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': match.group(4),
            'database': match.group(5)
        }
    return None


def create_env_config(components, use_url_format=True):
    """Create environment configuration"""
    if use_url_format:
        return f"DATABASE_URL=postgresql://{components['user']}:{components['password']}@{components['host']}:{components['port']}/{components['database']}"
    else:
        return f"""# Database configuration (host/port format)
DB_HOST={components['host']}
DB_PORT={components['port']}
DB_NAME={components['database']}
DB_USER={components['user']}
DB_PASSWORD={components['password']}
# DATABASE_URL=postgresql://{components['user']}:{components['password']}@{components['host']}:{components['port']}/{components['database']}"""


def get_supabase_info():
    """Get Supabase connection information from user"""
    print("🔧 Supabase Database Configuration")
    print("=" * 50)
    print("Please provide your Supabase database connection details.")
    print("You can find these in your Supabase Dashboard > Settings > Database")
    print()
    
    # Option 1: Full URL
    print("Option 1: Provide the full DATABASE_URL")
    database_url = input("DATABASE_URL (or press Enter to use host/port format): ").strip()
    
    if database_url:
        components = parse_database_url(database_url)
        if components:
            print("\n✅ Parsed DATABASE_URL successfully:")
            print(f"   Host: {components['host']}")
            print(f"   Port: {components['port']}")
            print(f"   Database: {components['database']}")
            print(f"   User: {components['user']}")
            print(f"   Password: {'*' * len(components['password'])}")
            return components
        else:
            print("❌ Invalid DATABASE_URL format. Please use host/port format instead.")
    
    # Option 2: Individual components
    print("\nOption 2: Provide individual connection details")
    
    # Default values for Supabase
    host = input("Host (e.g., db.xyz.supabase.co): ").strip()
    port = input("Port [5432]: ").strip() or "5432"
    database = input("Database [postgres]: ").strip() or "postgres"
    user = input("User [postgres]: ").strip() or "postgres"
    password = input("Password: ").strip()
    
    if not all([host, port, database, user, password]):
        print("❌ All fields are required!")
        return None
    
    return {
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password
    }


def test_connection(components):
    """Test database connection"""
    try:
        import psycopg2
        
        print("\n🔍 Testing database connection...")
        
        conn = psycopg2.connect(
            host=components['host'],
            port=components['port'],
            database=components['database'],
            user=components['user'],
            password=components['password'],
            sslmode='require'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"✅ Connection successful!")
        print(f"   PostgreSQL version: {version}")
        return True
        
    except ImportError:
        print("⚠️  psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def update_env_file(components, format_choice):
    """Update .env file with database configuration"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Remove existing database configuration
    new_lines = []
    skip_db_lines = False
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith('DATABASE_URL=') or \
           line_stripped.startswith('DB_HOST=') or \
           line_stripped.startswith('DB_PORT=') or \
           line_stripped.startswith('DB_NAME=') or \
           line_stripped.startswith('DB_USER=') or \
           line_stripped.startswith('DB_PASSWORD=') or \
           line_stripped.startswith('# SUPABASE_URL='):
            continue  # Skip existing database config
        new_lines.append(line)
    
    # Add new database configuration
    if format_choice == 'url':
        config = create_env_config(components, use_url_format=True)
        new_lines.append(f"{config}\n")
    else:
        config = create_env_config(components, use_url_format=False)
        new_lines.append(f"{config}\n")
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ Updated .env file with database configuration")
    return True


def main():
    """Main configuration function"""
    print("🚀 Mess Management System - Supabase Configuration")
    print("=" * 60)
    
    # Get Supabase connection details
    components = get_supabase_info()
    if not components:
        print("❌ Configuration cancelled.")
        return False
    
    # Test connection
    connection_ok = test_connection(components)
    
    if not connection_ok:
        proceed = input("\n⚠️  Connection test failed. Continue anyway? (y/N): ").strip().lower()
        if proceed != 'y':
            print("❌ Configuration cancelled.")
            return False
    
    # Choose format
    print("\n📝 Choose configuration format:")
    print("1. DATABASE_URL format (recommended)")
    print("2. Individual host/port variables")
    
    choice = input("Choice [1]: ").strip() or "1"
    format_choice = 'url' if choice == '1' else 'components'
    
    # Update .env file
    if update_env_file(components, format_choice):
        print("\n🎉 Supabase configuration completed successfully!")
        print("\nNext steps:")
        print("1. Run: python test_all_functions.py")
        print("2. Run: python manage.py migrate")
        print("3. Deploy to Render")
        return True
    else:
        print("❌ Failed to update configuration.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
