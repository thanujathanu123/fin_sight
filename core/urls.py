from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .api_views import (
    export_transactions, export_alerts, export_analytics_report,
    export_audit_log, export_ledger_summary, reports_list, report_detail,
    generate_report_now, report_instances, report_types, risk_forecast,
    predict_transaction_risk, trend_analysis, anomaly_detection
)

urlpatterns = [
    # Authentication Views
    path('login/', views.RBACLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='core/login.html', next_page='login'), name='logout'),
    path('register/', views.register, name='register'),

    # Password Reset Views
    path('password_reset/',
        auth_views.PasswordResetView.as_view(template_name='core/password_reset.html'),
        name='password_reset'),
    path('password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'),
        name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'),
        name='password_reset_confirm'),
    path('reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'),
        name='password_reset_complete'),

    # Password Change Views
    path('password_change/',
        auth_views.PasswordChangeView.as_view(template_name='core/password_change.html'),
        name='password_change'),
    path('password_change/done/',
        auth_views.PasswordChangeDoneView.as_view(template_name='core/password_change_done.html'),
        name='password_change_done'),

    # Main Application Views
    path('upload/', views.upload_ledger, name='upload_ledger'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.admin_user_management, name='admin_user_management'),
    path('auditor_dashboard/', views.auditor_dashboard, name='auditor_dashboard'),
    path('finance_dashboard/', views.finance_dashboard, name='finance_dashboard'),
    path('reviewer_dashboard/', views.reviewer_dashboard, name='reviewer_dashboard'),
    path('guest_dashboard/', views.guest_dashboard, name='guest_dashboard'),
    path('demo/', views.demo_landing, name='demo'),

    # API Endpoints for Data Export
    path('api/export/transactions/', export_transactions, name='api_export_transactions'),
    path('api/export/alerts/', export_alerts, name='api_export_alerts'),
    path('api/export/analytics/', export_analytics_report, name='api_export_analytics'),
    path('api/export/audit-log/', export_audit_log, name='api_export_audit_log'),
    path('api/export/ledger-summary/', export_ledger_summary, name='api_export_ledger_summary'),

    # API Endpoints for Automated Reporting
    path('api/reports/', reports_list, name='api_reports_list'),
    path('api/reports/types/', report_types, name='api_report_types'),
    path('api/reports/<int:report_id>/', report_detail, name='api_report_detail'),
    path('api/reports/<int:report_id>/generate/', generate_report_now, name='api_generate_report_now'),
    path('api/reports/<int:report_id>/instances/', report_instances, name='api_report_instances'),
    path('api/report-instances/', report_instances, name='api_all_report_instances'),

    # API Endpoints for Predictive Analytics
    path('api/analytics/risk-forecast/', risk_forecast, name='api_risk_forecast'),
    path('api/analytics/predict-transaction/', predict_transaction_risk, name='api_predict_transaction_risk'),
    path('api/analytics/trends/', trend_analysis, name='api_trend_analysis'),
    path('api/analytics/anomalies/', anomaly_detection, name='api_anomaly_detection'),
]
