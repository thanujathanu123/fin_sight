import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create default superuser for deployment'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Default superuser credentials
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@finsight.com')  
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'Admin@2024!')
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists, skipping creation.')
            )
            return
        
        # Create superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            user.is_staff = True
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superuser: {username}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )