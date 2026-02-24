import json
import asyncio
from datetime import datetime, timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Avg, Q


class DashboardConsumer(AsyncWebsocketConsumer):
    """Real-time dashboard updates for individual users"""

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'dashboard_{self.user_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial dashboard data
        await self.send_dashboard_data()

        # Start periodic updates
        asyncio.create_task(self.periodic_updates())

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def periodic_updates(self):
        """Send periodic dashboard updates"""
        while True:
            await asyncio.sleep(30)  # Update every 30 seconds
            await self.send_dashboard_data()

    async def send_dashboard_data(self):
        """Send current dashboard metrics"""
        data = await self.get_dashboard_data()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': data,
            'timestamp': datetime.now().isoformat()
        }))

    @database_sync_to_async
    def get_dashboard_data(self):
        """Get dashboard data for the user"""
        from django.contrib.auth.models import User
        from .models import Transaction, Alert, AuditLog

        try:
            user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            return {'error': 'User not found'}

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Transaction metrics
        transactions = Transaction.objects.filter(date__gte=thirty_days_ago)
        if not user.is_superuser and not user.groups.filter(name__in=['Admin', 'Auditor']).exists():
            transactions = transactions.filter(ledger_upload__uploaded_by=user)

        total_count = transactions.count()
        high_risk_count = transactions.filter(risk_score__gte=70).count()
        avg_risk = transactions.exclude(risk_score__isnull=True).aggregate(avg=Avg('risk_score'))['avg'] or 0

        transaction_data = {
            'total_count': total_count,
            'high_risk_count': high_risk_count,
            'avg_risk': avg_risk
        }

        # Alert metrics
        alerts = Alert.objects.filter(created_at__gte=thirty_days_ago)
        if not user.is_superuser and not user.groups.filter(name__in=['Admin', 'Auditor']).exists():
            alerts = alerts.filter(Q(created_by=user) | Q(assigned_to=user))

        total_alerts = alerts.count()
        resolved_alerts = alerts.filter(status='resolved').count()
        critical_alerts = alerts.filter(severity='critical').count()

        alert_data = {
            'total_alerts': total_alerts,
            'resolved_alerts': resolved_alerts,
            'critical_alerts': critical_alerts
        }

        # Recent activity
        recent_activity = list(AuditLog.objects.filter(
            timestamp__gte=thirty_days_ago
        ).select_related('user').order_by('-timestamp')[:5].values(
            'timestamp', 'action', 'model_name', 'user__username'
        ))

        return {
            'transactions': transaction_data,
            'alerts': alert_data,
            'recent_activity': recent_activity,
            'last_updated': now.isoformat()
        }


class AnalyticsConsumer(AsyncWebsocketConsumer):
    """Real-time analytics broadcasting"""

    async def connect(self):
        self.room_group_name = 'analytics'

        # Join analytics group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial analytics data
        await self.send_analytics_data()

    async def disconnect(self, close_code):
        # Leave analytics group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def send_analytics_data(self):
        """Send current analytics data"""
        data = await self.get_analytics_data()
        await self.send(text_data=json.dumps({
            'type': 'analytics_update',
            'data': data,
            'timestamp': datetime.now().isoformat()
        }))

    @database_sync_to_async
    def get_analytics_data(self):
        """Get system-wide analytics data"""
        from .models import Transaction, Alert, LedgerUpload

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # System metrics
        total_transactions = Transaction.objects.filter(date__gte=thirty_days_ago).count()
        high_risk_transactions = Transaction.objects.filter(
            date__gte=thirty_days_ago, risk_score__gte=70
        ).count()

        total_alerts = Alert.objects.filter(created_at__gte=thirty_days_ago).count()
        resolved_alerts = Alert.objects.filter(
            created_at__gte=thirty_days_ago, status='resolved'
        ).count()

        # Risk distribution
        risk_distribution = {
            'low': Transaction.objects.filter(
                date__gte=thirty_days_ago, risk_score__lt=40
            ).count(),
            'medium': Transaction.objects.filter(
                date__gte=thirty_days_ago, risk_score__gte=40, risk_score__lt=70
            ).count(),
            'high': high_risk_transactions
        }

        # Processing status
        processing_status = {
            'pending': LedgerUpload.objects.filter(status='pending').count(),
            'processing': LedgerUpload.objects.filter(status='processing').count(),
            'completed': LedgerUpload.objects.filter(status='completed').count(),
            'error': LedgerUpload.objects.filter(status='error').count()
        }

        return {
            'total_transactions': total_transactions,
            'high_risk_transactions': high_risk_transactions,
            'risk_rate': round((high_risk_transactions / total_transactions * 100), 1) if total_transactions > 0 else 0,
            'total_alerts': total_alerts,
            'resolved_alerts': resolved_alerts,
            'resolution_rate': round((resolved_alerts / total_alerts * 100), 1) if total_alerts > 0 else 0,
            'risk_distribution': risk_distribution,
            'processing_status': processing_status,
            'last_updated': now.isoformat()
        }


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notifications for users"""

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'notifications_{self.user_id}'

        # Join notification group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send any pending notifications
        await self.send_pending_notifications()

    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def send_pending_notifications(self):
        """Send pending notifications"""
        notifications = await self.get_pending_notifications()
        for notification in notifications:
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'data': notification,
                'timestamp': datetime.now().isoformat()
            }))

    @database_sync_to_async
    def get_pending_notifications(self):
        """Get pending notifications for the user"""
        from django.contrib.auth.models import User
        from .models import Alert

        try:
            user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            return []

        # Get recent alerts assigned to user
        recent_alerts = Alert.objects.filter(
            assigned_to=user,
            status='new',
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')[:5]

        notifications = []
        for alert in recent_alerts:
            notifications.append({
                'id': alert.id,
                'type': 'alert',
                'title': alert.title,
                'message': f"New alert: {alert.title}",
                'severity': alert.severity,
                'created_at': alert.created_at.isoformat(),
                'url': f'/reviewer_dashboard/?alert={alert.id}'
            })

        return notifications

    # Receive message from room group
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps(event['data']))


# Utility functions for broadcasting updates
async def broadcast_dashboard_update(user_id):
    """Broadcast dashboard update to specific user"""
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()

    await channel_layer.group_send(
        f'dashboard_{user_id}',
        {
            'type': 'dashboard_update',
            'data': {},  # Will be populated by consumer
        }
    )


async def broadcast_analytics_update():
    """Broadcast analytics update to all connected clients"""
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()

    await channel_layer.group_send(
        'analytics',
        {
            'type': 'analytics_update',
            'data': {},  # Will be populated by consumer
        }
    )


async def send_user_notification(user_id, notification_data):
    """Send notification to specific user"""
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()

    await channel_layer.group_send(
        f'notifications_{user_id}',
        {
            'type': 'notification_message',
            'data': notification_data
        }
    )