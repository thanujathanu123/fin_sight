from django.contrib import admin
from django.utils.html import format_html
from .models import LedgerUpload, Transaction, Alert, RiskProfile, AuditLog


@admin.register(LedgerUpload)
class LedgerUploadAdmin(admin.ModelAdmin):
    list_display = [
        'filename',
        'uploaded_by',
        'status',
        'uploaded_at',
        'risk_score_display',
        'high_risk_count',
        'transaction_count',
        'processing_time_display'
    ]
    list_filter = ['status', 'uploaded_at', 'uploaded_by']
    search_fields = ['filename', 'uploaded_by__username']
    readonly_fields = [
        'risk_score',
        'high_risk_count',
        'transaction_count',
        'processed_at',
        'processing_time',
        'error_message'
    ]
    ordering = ['-uploaded_at']

    def risk_score_display(self, obj):
        if obj.risk_score is not None:
            # Ensure we work with numeric value, not SafeString
            score = float(obj.risk_score)
            color = 'red' if score > 70 else 'orange' if score > 40 else 'green'
            # Format the score first, then use format_html
            formatted_score = f"{score:.1f}"
            return format_html(
                '<span style="color: {};">{}%</span>',
                color,
                formatted_score
            )
        return '-'
    risk_score_display.short_description = 'Risk Score'

    def processing_time_display(self, obj):
        if obj.processing_time:
            # Ensure we work with numeric value, not SafeString
            seconds = float(obj.processing_time.total_seconds())
            return f"{seconds:.1f}s"
        return '-'
    processing_time_display.short_description = 'Processing Time'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference_id',
        'date',
        'amount',
        'description_truncated',
        'risk_score_display',
        'status',
        'ledger_upload'
    ]
    list_filter = ['status', 'category', 'date', 'ledger_upload']
    search_fields = ['reference_id', 'description']
    readonly_fields = ['risk_score', 'risk_factors']
    ordering = ['-date']

    def description_truncated(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_truncated.short_description = 'Description'

    def risk_score_display(self, obj):
        if obj.risk_score is not None:
            # Ensure we work with numeric value, not SafeString
            score = float(obj.risk_score)
            color = 'red' if score > 70 else 'orange' if score > 40 else 'green'
            # Format the score first, then use format_html
            formatted_score = f"{score:.1f}"
            return format_html(
                '<span style="color: {};">{}%</span>',
                color,
                formatted_score
            )
        return '-'
    risk_score_display.short_description = 'Risk Score'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'severity',
        'status',
        'transaction_reference',
        'assigned_to',
        'created_at'
    ]
    list_filter = ['severity', 'status', 'created_at', 'assigned_to']
    search_fields = ['title', 'description', 'transaction__reference_id']
    ordering = ['-created_at']

    def transaction_reference(self, obj):
        return obj.transaction.reference_id
    transaction_reference.short_description = 'Transaction'


@admin.register(RiskProfile)
class RiskProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'industry', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr']
    list_filter = ['action', 'model_name', 'timestamp', 'user']
    search_fields = ['user__username', 'model_name', 'object_repr']
    readonly_fields = ['timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 'changes', 'ip_address', 'user_agent']
    ordering = ['-timestamp']