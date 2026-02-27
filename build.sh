#!/bin/bash
# Build script for Render deployment

set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating default superuser..."
# Use Django's built-in superuser creation with environment variables
export DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin}
export DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@finsight.com}
export DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-AdminPassword123!}

# Create superuser only if none exists
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('Superuser exists, skipping') if User.objects.filter(is_superuser=True).exists() else None" 2>/dev/null || {
    echo "Creating superuser with Django's createsuperuser command..."
    python manage.py createsuperuser --noinput --username="$DJANGO_SUPERUSER_USERNAME" --email="$DJANGO_SUPERUSER_EMAIL" || {
        echo "WARNING: Superuser creation failed, trying fallback method..."
        python manage.py create_default_superuser || echo "Fallback also failed, but continuing..."
    }
}

echo "Build complete!"
