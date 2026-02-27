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
        
        self.stdout.write(f'🔍 Checking for existing superusers...')
        
        existing_superusers = User.objects.filter(is_superuser=True)
        if existing_superusers.exists():
            usernames = [u.username for u in existing_superusers]
            self.stdout.write(
                self.style.WARNING(f'✅ Superusers already exist: {", ".join(usernames)}')
            )
            return
        
        # Create superuser
        self.stdout.write(f'👤 Creating superuser: {username}')
        try:
            with transaction.atomic():
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully created superuser: {username}')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating superuser: {str(e)}')
            )
            # Try creating with basic attributes if create_superuser fails
            try:
                with transaction.atomic():
                    user = User(
                        username=username,
                        email=email,
                        is_staff=True,
                        is_superuser=True,
                        is_active=True
                    )
                    user.set_password(password)
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Fallback creation successful for: {username}')
                    )
            except Exception as e2:
                self.stdout.write(
                    self.style.ERROR(f'❌ Fallback also failed: {str(e2)}')
                )