#!/usr/bin/env bash
# build.sh - Render build script for Django application

set -o errexit  # exit on error

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    netcat-traditional \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    tk-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
# Install wheel first for better package building
pip install wheel setuptools

# Try to install packages with better error handling
echo "Attempting to install all dependencies..."
if ! pip install -r requirements.txt --no-cache-dir; then
    echo "Full installation failed, trying minimal requirements..."

    # Use minimal requirements as fallback
    if pip install -r requirements-minimal.txt --no-cache-dir; then
        echo "Minimal requirements installed successfully"

        # Try to add Pillow separately
        echo "Attempting to install Pillow for QR code images..."
        pip install Pillow==10.4.0 --no-cache-dir || echo "Pillow installation failed, QR codes will be text-only"

        # Try to add optional packages
        echo "Installing optional packages..."
        pip install celery==5.3.4 redis==5.0.1 || echo "Celery/Redis installation failed, background tasks disabled"
        pip install cloudinary==1.36.0 || echo "Cloudinary installation failed, file uploads may not work"
        pip install sentry-sdk==2.14.0 || echo "Sentry installation failed, error monitoring disabled"
    else
        echo "Even minimal installation failed, this may cause issues"
        exit 1
    fi
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Check for new migrations and create them if needed
echo "Checking for new migrations..."
python manage.py makemigrations --check --dry-run || {
    echo "Creating new migrations..."
    python manage.py makemigrations
}

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create logs directory if it doesn't exist
echo "Creating logs directory..."
mkdir -p logs

# Create superuser if environment variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser if it doesn't exist..."
    python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if username and password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created successfully')
else:
    print('Superuser already exists or credentials not provided')
"
else
    echo "Skipping superuser creation (set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD to create)"
fi

echo "Build completed successfully!"