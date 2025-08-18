#!/usr/bin/env python3
"""
Test Build Process Script
Simulates the Render build process locally to verify everything works
"""

import os
import sys
import subprocess
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.db import connection


def run_command(command, description):
    """Run a shell command and return success status"""
    print(f"\n🔧 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success: {description}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Failed: {description}")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_django_commands():
    """Test Django management commands"""
    print("\n🐍 Testing Django Commands")
    print("=" * 50)
    
    # Test makemigrations check
    try:
        print("\n🔍 Checking for new migrations...")
        call_command('makemigrations', '--check', '--dry-run', verbosity=0)
        print("✅ No new migrations needed")
    except SystemExit:
        print("⚠️  New migrations would be created")
        try:
            call_command('makemigrations', verbosity=1)
            print("✅ New migrations created")
        except Exception as e:
            print(f"❌ Failed to create migrations: {e}")
            return False
    
    # Test migrate
    try:
        print("\n🗄️  Running migrations...")
        call_command('migrate', verbosity=1)
        print("✅ Migrations applied successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    # Test collectstatic
    try:
        print("\n📁 Collecting static files...")
        call_command('collectstatic', '--noinput', '--clear', verbosity=1)
        print("✅ Static files collected")
    except Exception as e:
        print(f"❌ Static collection failed: {e}")
        return False
    
    return True


def test_database_connection():
    """Test database connectivity"""
    print("\n🗄️  Testing Database Connection")
    print("=" * 50)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                db_name = connection.settings_dict['NAME']
                db_engine = connection.settings_dict['ENGINE']
                print(f"✅ Database connected: {db_name}")
                print(f"   Engine: {db_engine}")
                return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_environment_variables():
    """Test critical environment variables"""
    print("\n🔧 Testing Environment Variables")
    print("=" * 50)
    
    from django.conf import settings
    
    required_vars = {
        'DJANGO_SECRET_KEY': getattr(settings, 'SECRET_KEY', None),
        'TELEGRAM_BOT_TOKEN': getattr(settings, 'TELEGRAM_BOT_TOKEN', None),
        'QR_SECRET': getattr(settings, 'QR_SECRET', None),
    }
    
    all_good = True
    for var_name, value in required_vars.items():
        if value and value not in ['your-secret-key-here', 'your-bot-token-here']:
            print(f"✅ {var_name}: Configured")
        else:
            print(f"❌ {var_name}: Not configured or using default")
            all_good = False
    
    return all_good


def test_gunicorn_config():
    """Test if gunicorn can start the application"""
    print("\n🚀 Testing Gunicorn Configuration")
    print("=" * 50)
    
    # Test if wsgi module can be imported
    try:
        from config.wsgi import application
        print("✅ WSGI application can be imported")
    except Exception as e:
        print(f"❌ WSGI import failed: {e}")
        return False
    
    # Test gunicorn command syntax (dry run)
    gunicorn_cmd = "gunicorn config.wsgi:application --check-config"
    return run_command(gunicorn_cmd, "Gunicorn configuration check")


def simulate_build_process():
    """Simulate the complete build process"""
    print("\n🏗️  Simulating Complete Build Process")
    print("=" * 50)
    
    steps = [
        ("pip install --upgrade pip", "Upgrading pip"),
        ("python manage.py check", "Django system check"),
    ]
    
    all_success = True
    for cmd, desc in steps:
        if not run_command(cmd, desc):
            all_success = False
    
    return all_success


def main():
    """Main test function"""
    print("🧪 Testing Render Build Process Locally")
    print("=" * 60)
    print("This script simulates what happens during Render deployment")
    print("to verify everything will work correctly.\n")
    
    # Run all tests
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Database Connection", test_database_connection),
        ("Django Commands", test_django_commands),
        ("Gunicorn Configuration", test_gunicorn_config),
        ("Build Process", simulate_build_process),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Build Test Summary:")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your app is ready for Render deployment.")
        print("\nNext steps:")
        print("1. Push your code to GitHub")
        print("2. Set environment variables in Render dashboard")
        print("3. Deploy using the configured build.sh and start commands")
        print("4. Monitor deployment logs for any issues")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Fix these issues before deploying.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
