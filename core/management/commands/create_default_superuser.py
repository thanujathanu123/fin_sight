import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

class Command(BaseCommand):
    help = 'Create default superuser for deployment'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Default superuser credentials (12+ chars for password validation)
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@finsight.com')  
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'AdminPassword123!')
        
        self.stdout.write(f'Attempting to create superuser: {username}')
        
        # Check if any superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists, skipping creation.')
            )
            return
        
        # Create superuser with transaction
        try:
            with transaction.atomic():
                # Create superuser without validation to avoid password issues
                user = User(
                    username=username,
                    email=email,
                    is_staff=True,
                    is_superuser=True,
                    is_active=True
                )
                user.set_password(password)  # This handles password hashing
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser: {username} with email: {email}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )