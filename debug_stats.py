#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finsight.settings')
django.setup()

from core.models import Transaction, Alert
from django.utils import timezone
from django.db.models import Count, Avg
from django.contrib.auth.models import User

# Simulate reviewer_dashboard logic
now = timezone.now()
thirty_days_ago = now - timezone.timedelta(days=30)

print(f"Current time: {now}")
print(f"30 days ago: {thirty_days_ago}")

# Get user
user = User.objects.first()
print(f"User: {user}")

my_alerts = Alert.objects.filter(
    assigned_to=user,
    created_at__gte=thirty_days_ago,
).select_related('transaction', 'transaction__ledger_upload').order_by('-created_at')

print(f"My alerts count: {my_alerts.count()}")

# Calculate overall risk score
recent_transactions = Transaction.objects.filter(date__gte=thirty_days_ago)
if recent_transactions.exists():
    overall_risk_score = recent_transactions.aggregate(avg_risk=Avg('risk_score'))['avg_risk'] or 0
else:
    overall_risk_score = Transaction.objects.aggregate(avg_risk=Avg('risk_score'))['avg_risk'] or 0

print(f"Overall risk score: {overall_risk_score}")

stats = {
    'risk_score': overall_risk_score,
    'reviewed': my_alerts.filter(status='resolved').count(),
    'assigned': my_alerts.count(),
    'pending_review': my_alerts.filter(status='new').count(),
    'in_progress': my_alerts.filter(status='in_progress').count(),
}

print(f"Stats: {stats}")

# Check what _format_duration returns
def _format_duration(duration):
    if not duration:
        return "—"
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

avg_resolution_time = _format_duration(
    my_alerts.filter(resolved_at__isnull=False).aggregate(
        avg_duration=Avg(
            timezone.timedelta(seconds=0)  # This is a placeholder
        )
    )['avg_duration']
)

print(f"Avg resolution time: {avg_resolution_time}")