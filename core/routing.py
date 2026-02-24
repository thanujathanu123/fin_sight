from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/dashboard/(?P<user_id>\d+)/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/analytics/$', consumers.AnalyticsConsumer.as_asgi()),
    re_path(r'ws/notifications/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
]