import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Debug user accounts and their permissions'

    def handle(self, *args, **options):
        User = get_user_model()
        
        self.stdout.write('🔍 DEBUG: Current user accounts in database:')
        self.stdout.write('-' * 50)
        
        try:
            users = User.objects.all()
            if not users.exists():
                self.stdout.write('❌ No users found in database!')
                return
                
            for user in users:
                self.stdout.write(f'👤 Username: {user.username}')
                self.stdout.write(f'   📧 Email: {user.email}')
                self.stdout.write(f'   🛡️ Staff: {user.is_staff}')
                self.stdout.write(f'   ⭐ Superuser: {user.is_superuser}')
                self.stdout.write(f'   ✅ Active: {user.is_active}')
                self.stdout.write('-' * 30)
                
        except Exception as e:
            self.stdout.write(f'❌ Database error: {str(e)}')