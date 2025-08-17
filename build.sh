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

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create logs directory if it doesn't exist
echo "Creating logs directory..."
mkdir -p logs

# Create superuser if it doesn't exist (optional)
# echo "Creating superuser..."
# python manage.py shell -c "
# from django.contrib.auth import get_user_model
# User = get_user_model()
# if not User.objects.filter(username='admin').exists():
#     User.objects.create_superuser('admin', 'admin@example.com', 'changeme')
#     print('Superuser created')
# else:
#     print('Superuser already exists')
# "

echo "Build completed successfully!"