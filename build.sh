#!/usr/bin/env bash
# build.sh - Render build script for Django application

set -o errexit  # exit on error

# Install system dependencies
echo "Installing system dependencies..."
apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    netcat-traditional

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

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