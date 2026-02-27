from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def debug_users_api(request):
    """Debug API endpoint to check user creation status"""
    try:
        User = get_user_model()
        users_data = []
        
        for user in User.objects.all():
            users_data.append({
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
            })
        
        return JsonResponse({
            'status': 'success',
            'total_users': len(users_data),
            'superusers': [u for u in users_data if u['is_superuser']],
            'staff_users': [u for u in users_data if u['is_staff']],
            'all_users': users_data
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })