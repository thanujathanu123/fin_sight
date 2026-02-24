from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
import uuid


class RiskProfile(models.Model):
    """Configurable risk thresholds and rules"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    industry = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    
    # Risk thresholds
    amount_threshold = models.DecimalField(
        max_digits=15, decimal_places=2, 
        help_text="Transaction amount that triggers heightened scrutiny"
    )
    frequency_threshold = models.IntegerField(
        help_text="Number of transactions within time window that triggers alerts"
    )
    time_window_hours = models.IntegerField(
        help_text="Time window for frequency analysis (in hours)"
    )
    
    # ML model parameters (stored as JSON)
    ml_parameters = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} v{self.version}"


class Transaction(models.Model):
    """Financial transaction with risk scoring"""
    CATEGORIES = [
        ('payment', 'Payment'),
        ('transfer', 'Transfer'),
        ('withdrawal', 'Withdrawal'),
        ('deposit', 'Deposit'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('flagged', 'Flagged for Review'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateTimeField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORIES)
    reference_id = models.CharField(max_length=100, unique=True)
    
    # Risk assessment
    risk_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0-100 risk score, higher means more risky"
    )
    risk_factors = models.JSONField(
        default=dict,
        help_text="Factors contributing to risk score"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ledger_upload = models.ForeignKey('LedgerUpload', on_delete=models.CASCADE)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='reviewed_transactions'
    )
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'risk_score']),
            models.Index(fields=['status', 'risk_score']),
        ]

    def __str__(self):
        return f"{self.reference_id} - {self.amount} ({self.status})"


class Alert(models.Model):
    """Risk-based alerts and notifications"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Relations
    transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_alerts'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_alerts'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.severity} - {self.title} ({self.status})"


class AuditLog(models.Model):
    """Comprehensive activity logging"""
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} {self.model_name} at {self.timestamp}"


class Report(models.Model):
    """Automated report configurations"""
    REPORT_TYPES = [
        ('transaction_summary', 'Transaction Summary'),
        ('risk_analysis', 'Risk Analysis Report'),
        ('alert_summary', 'Alert Summary'),
        ('compliance_report', 'Compliance Report'),
        ('user_activity', 'User Activity Report'),
    ]

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)

    # Report parameters
    date_range_days = models.PositiveIntegerField(default=30, help_text="Number of days to include in report")
    include_charts = models.BooleanField(default=True)
    include_raw_data = models.BooleanField(default=False)

    # Recipients
    recipients = models.JSONField(default=list, help_text="List of email addresses to send report to")

    # Filters
    risk_threshold_min = models.FloatField(null=True, blank=True)
    risk_threshold_max = models.FloatField(null=True, blank=True)
    include_high_risk_only = models.BooleanField(default=False)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"

    def calculate_next_run(self):
        """Calculate when this report should next run"""
        from datetime import datetime, timedelta
        from django.utils import timezone

        now = timezone.now()

        if self.frequency == 'daily':
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif self.frequency == 'weekly':
            # Next Monday at 9 AM
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_run = (now + timedelta(days=days_until_monday)).replace(hour=9, minute=0, second=0, microsecond=0)
        elif self.frequency == 'monthly':
            # First day of next month at 9 AM
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
        elif self.frequency == 'quarterly':
            # First day of next quarter at 9 AM
            current_quarter = ((now.month - 1) // 3) + 1
            if current_quarter == 4:
                next_quarter_month = 1
                next_year = now.year + 1
            else:
                next_quarter_month = (current_quarter * 3) + 1
                next_year = now.year

            next_run = now.replace(year=next_year, month=next_quarter_month, day=1, hour=9, minute=0, second=0, microsecond=0)
        else:
            next_run = now + timedelta(days=1)

        self.next_run = next_run
        return next_run


class ReportInstance(models.Model):
    """Individual report generation instances"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Date range for this instance
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Generated files
    pdf_file = models.FileField(upload_to='reports/pdf/', null=True, blank=True)
    excel_file = models.FileField(upload_to='reports/excel/', null=True, blank=True)
    csv_file = models.FileField(upload_to='reports/csv/', null=True, blank=True)

    # Results summary
    summary_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report.name} - {self.start_date.date()} to {self.end_date.date()}"

    def get_file_urls(self):
        """Get URLs for generated files"""
        urls = {}
        if self.pdf_file:
            urls['pdf'] = self.pdf_file.url
        if self.excel_file:
            urls['excel'] = self.excel_file.url
        if self.csv_file:
            urls['csv'] = self.csv_file.url
        return urls


class LedgerUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Analysis'),
        ('processing', 'Processing'),
        ('completed', 'Analysis Complete'),
        ('error', 'Error'),
    ]
    
    file = models.FileField(
        upload_to='ledgers/',
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx'])]
    )
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(blank=True)
    
    # Risk analysis results
    risk_score = models.FloatField(null=True, blank=True)
    risk_factors = models.JSONField(default=dict)
    transaction_count = models.IntegerField(default=0)
    high_risk_count = models.IntegerField(default=0)
    
    # Processing metadata
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_time = models.DurationField(null=True, blank=True)
    
    # Risk profile used
    risk_profile = models.ForeignKey(
        RiskProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Risk profile used for analysis"
    )
    
    def __str__(self):
        return f"{self.filename} by {self.uploaded_by} ({self.status})"

    class Meta:
        ordering = ['-uploaded_at']
