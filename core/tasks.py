from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Max, Q
from .models import (
    LedgerUpload, Transaction, RiskProfile, Alert,
    Report, ReportInstance, User, AuditLog
)
from .risk_engine.processor import process_ledger_file
from .risk_engine.analysis import RiskAnalysisEngine
from .exports import AnalyticsReportExporter, TransactionExporter, AlertExporter
import logging
import os

logger = logging.getLogger(__name__)

@shared_task
def analyze_transaction(transaction_id):
    """
    Analyze a single transaction for risk.
    """
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        engine = RiskAnalysisEngine()
        risk_score = engine.analyze_transaction(transaction)
        
        # Update transaction risk score
        transaction.risk_score = risk_score
        transaction.save()

        # Update user's risk profile
        profile, _ = RiskProfile.objects.get_or_create(user=transaction.user)
        profile.update_risk_score()

        # Create alert if risk score is high
        if risk_score > 0.8:  # High risk threshold
            Alert.objects.create(
                user=transaction.user,
                transaction=transaction,
                risk_score=risk_score,
                message=f"High risk transaction detected (score: {risk_score:.2f})"
            )
        
        logger.info(f'Successfully analyzed transaction {transaction_id} with risk score {risk_score:.2f}')
        return True
    except Exception as e:
        logger.error(f'Error analyzing transaction {transaction_id}: {str(e)}', exc_info=True)
        return False

@shared_task
def update_all_risk_profiles():
    """
    Periodic task to update all user risk profiles.
    """
    try:
        profiles = RiskProfile.objects.all()
        updated_count = 0
        for profile in profiles:
            profile.update_risk_score()
            updated_count += 1
        logger.info(f'Successfully updated {updated_count} risk profiles')
        return True
    except Exception as e:
        logger.error(f'Error updating risk profiles: {str(e)}', exc_info=True)
        return False

@shared_task
def cleanup_old_alerts(days=30):
    """
    Periodic task to clean up old alerts.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = Alert.objects.filter(created_at__lt=cutoff_date).delete()[0]
        logger.info(f'Successfully deleted {deleted_count} old alerts')
        return True
    except Exception as e:
        logger.error(f'Error cleaning up old alerts: {str(e)}', exc_info=True)
        return False

@shared_task
def process_ledger_upload(upload_id):
    """
    Celery task to process a ledger upload asynchronously
    """
    try:
        # Get the upload
        upload = LedgerUpload.objects.get(id=upload_id)
        
        # Get file path
        file_path = upload.file.path
        
        # Process the file
        overall_risk, high_risk_count = process_ledger_file(file_path, upload)
        
        logger.info(
            f'Successfully processed ledger upload {upload_id}. '
            f'Risk score: {overall_risk:.2f}, '
            f'High risk transactions: {high_risk_count}'
        )
        
        return True
        
    except LedgerUpload.DoesNotExist:
        logger.error(f'LedgerUpload {upload_id} not found')
        return False
        
    except Exception as e:
        logger.error(f'Error processing ledger upload {upload_id}: {str(e)}', exc_info=True)
        
        # Update upload status
        try:
            upload = LedgerUpload.objects.get(id=upload_id)
            upload.status = 'error'
            upload.error_message = str(e)
            upload.save()
        except Exception as e2:
            logger.error(f'Error updating upload status: {str(e2)}', exc_info=True)

        return False


@shared_task
def generate_scheduled_reports():
    """
    Generate all scheduled reports that are due to run
    """
    try:
        now = timezone.now()
        due_reports = Report.objects.filter(
            is_active=True,
            next_run__lte=now
        )

        generated_count = 0
        for report in due_reports:
            try:
                generate_report_instance.delay(report.id)
                report.last_run = now
                report.calculate_next_run()
                report.save()
                generated_count += 1
                logger.info(f'Scheduled report generation for: {report.name}')
            except Exception as e:
                logger.error(f'Error scheduling report {report.id}: {str(e)}', exc_info=True)

        logger.info(f'Successfully scheduled {generated_count} reports for generation')
        return True
    except Exception as e:
        logger.error(f'Error in generate_scheduled_reports: {str(e)}', exc_info=True)
        return False


@shared_task
def generate_report_instance(report_id):
    """
    Generate a specific report instance
    """
    try:
        report = Report.objects.get(id=report_id)
        now = timezone.now()

        # Calculate date range
        end_date = now
        start_date = end_date - timedelta(days=report.date_range_days)

        # Create report instance
        instance = ReportInstance.objects.create(
            report=report,
            status='generating',
            start_date=start_date,
            end_date=end_date
        )

        # Generate report based on type
        if report.report_type == 'transaction_summary':
            success = _generate_transaction_summary_report(instance)
        elif report.report_type == 'risk_analysis':
            success = _generate_risk_analysis_report(instance)
        elif report.report_type == 'alert_summary':
            success = _generate_alert_summary_report(instance)
        elif report.report_type == 'compliance_report':
            success = _generate_compliance_report(instance)
        elif report.report_type == 'user_activity':
            success = _generate_user_activity_report(instance)
        else:
            raise ValueError(f'Unknown report type: {report.report_type}')

        if success:
            instance.status = 'completed'
            instance.completed_at = timezone.now()
            instance.save()

            # Send report via email if recipients are configured
            if report.recipients:
                send_report_email.delay(instance.id)

            logger.info(f'Successfully generated report instance {instance.id}')
            return True
        else:
            instance.status = 'failed'
            instance.error_message = 'Report generation failed'
            instance.save()
            return False

    except Exception as e:
        logger.error(f'Error generating report instance for report {report_id}: {str(e)}', exc_info=True)
        try:
            instance = ReportInstance.objects.get(report_id=report_id, status='generating')
            instance.status = 'failed'
            instance.error_message = str(e)
            instance.save()
        except:
            pass
        return False


def _generate_transaction_summary_report(instance):
    """Generate transaction summary report"""
    try:
        # Get filtered transactions
        queryset = Transaction.objects.filter(
            date__gte=instance.start_date,
            date__lte=instance.end_date
        )

        # Apply report filters
        if instance.report.risk_threshold_min is not None:
            queryset = queryset.filter(risk_score__gte=instance.report.risk_threshold_min)
        if instance.report.risk_threshold_max is not None:
            queryset = queryset.filter(risk_score__lte=instance.report.risk_threshold_max)
        if instance.report.include_high_risk_only:
            queryset = queryset.filter(risk_score__gte=70)

        # Generate files
        timestamp = instance.created_at.strftime('%Y%m%d_%H%M%S')

        if instance.report.include_raw_data:
            # Generate CSV
            csv_filename = f'transaction_summary_{timestamp}.csv'
            csv_response = TransactionExporter.export_csv(queryset, csv_filename)
            instance.csv_file.save(csv_filename, csv_response.file_to_stream(), save=False)

        # Generate Excel
        excel_filename = f'transaction_summary_{timestamp}.xlsx'
        excel_response = TransactionExporter.export_excel(queryset, excel_filename)
        instance.excel_file.save(excel_filename, excel_response.file_to_stream(), save=False)

        # Generate PDF summary
        pdf_filename = f'transaction_summary_{timestamp}.pdf'
        pdf_response = AnalyticsReportExporter.export_summary_pdf(
            instance.start_date, instance.end_date, pdf_filename
        )
        instance.pdf_file.save(pdf_filename, pdf_response.file_to_stream(), save=False)

        # Store summary data
        summary = AnalyticsReportExporter.generate_summary_report(
            instance.start_date, instance.end_date
        )
        instance.summary_data = summary

        return True
    except Exception as e:
        logger.error(f'Error generating transaction summary report: {str(e)}', exc_info=True)
        return False


def _generate_risk_analysis_report(instance):
    """Generate risk analysis report"""
    try:
        # Get high-risk transactions
        high_risk_transactions = Transaction.objects.filter(
            date__gte=instance.start_date,
            date__lte=instance.end_date,
            risk_score__gte=70
        ).order_by('-risk_score')

        # Get risk distribution
        risk_dist = {
            'low': Transaction.objects.filter(
                date__gte=instance.start_date, date__lte=instance.end_date, risk_score__lt=40
            ).count(),
            'medium': Transaction.objects.filter(
                date__gte=instance.start_date, date__lte=instance.end_date,
                risk_score__gte=40, risk_score__lt=70
            ).count(),
            'high': high_risk_transactions.count()
        }

        # Generate files
        timestamp = instance.created_at.strftime('%Y%m%d_%H%M%S')

        if instance.report.include_raw_data:
            csv_filename = f'risk_analysis_{timestamp}.csv'
            csv_response = TransactionExporter.export_csv(high_risk_transactions, csv_filename)
            instance.csv_file.save(csv_filename, csv_response.file_to_stream(), save=False)

        # Generate Excel with high-risk transactions
        excel_filename = f'risk_analysis_{timestamp}.xlsx'
        excel_response = TransactionExporter.export_excel(high_risk_transactions, excel_filename)
        instance.excel_file.save(excel_filename, excel_response.file_to_stream(), save=False)

        # Store summary data
        instance.summary_data = {
            'high_risk_transactions': high_risk_transactions.count(),
            'risk_distribution': risk_dist,
            'top_risk_transaction': high_risk_transactions.first().description if high_risk_transactions.exists() else None
        }

        return True
    except Exception as e:
        logger.error(f'Error generating risk analysis report: {str(e)}', exc_info=True)
        return False


def _generate_alert_summary_report(instance):
    """Generate alert summary report"""
    try:
        # Get alerts in date range
        alerts = Alert.objects.filter(
            created_at__gte=instance.start_date,
            created_at__lte=instance.end_date
        ).select_related('transaction')

        # Generate files
        timestamp = instance.created_at.strftime('%Y%m%d_%H%M%S')

        if instance.report.include_raw_data:
            csv_filename = f'alert_summary_{timestamp}.csv'
            csv_response = AlertExporter.export_csv(alerts, csv_filename)
            instance.csv_file.save(csv_filename, csv_response.file_to_stream(), save=False)

        excel_filename = f'alert_summary_{timestamp}.xlsx'
        excel_response = AlertExporter.export_excel(alerts, excel_filename)
        instance.excel_file.save(excel_filename, excel_response.file_to_stream(), save=False)

        # Store summary data
        alert_stats = alerts.aggregate(
            total=Count('id'),
            resolved=Count('id', filter=Q(status='resolved')),
            critical=Count('id', filter=Q(severity='critical'))
        )

        instance.summary_data = {
            'total_alerts': alert_stats['total'] or 0,
            'resolved_alerts': alert_stats['resolved'] or 0,
            'critical_alerts': alert_stats['critical'] or 0,
            'resolution_rate': round((alert_stats['resolved'] or 0) / (alert_stats['total'] or 1) * 100, 1)
        }

        return True
    except Exception as e:
        logger.error(f'Error generating alert summary report: {str(e)}', exc_info=True)
        return False


def _generate_compliance_report(instance):
    """Generate compliance report"""
    try:
        # Get compliance-related data
        total_transactions = Transaction.objects.filter(
            date__gte=instance.start_date, date__lte=instance.end_date
        ).count()

        reviewed_transactions = Transaction.objects.filter(
            date__gte=instance.start_date, date__lte=instance.end_date
        ).exclude(reviewed_by__isnull=True).count()

        high_risk_reviewed = Transaction.objects.filter(
            date__gte=instance.start_date, date__lte=instance.end_date,
            risk_score__gte=70
        ).exclude(reviewed_by__isnull=True).count()

        # Store summary data
        instance.summary_data = {
            'total_transactions': total_transactions,
            'reviewed_transactions': reviewed_transactions,
            'review_coverage': round(reviewed_transactions / (total_transactions or 1) * 100, 1),
            'high_risk_reviewed': high_risk_reviewed,
            'compliance_status': 'Good' if reviewed_transactions / (total_transactions or 1) > 0.8 else 'Needs Attention'
        }

        return True
    except Exception as e:
        logger.error(f'Error generating compliance report: {str(e)}', exc_info=True)
        return False


def _generate_user_activity_report(instance):
    """Generate user activity report"""
    try:
        # Get user activity data
        user_activity = AuditLog.objects.filter(
            timestamp__gte=instance.start_date,
            timestamp__lte=instance.end_date
        ).values('user__username').annotate(
            actions=Count('id'),
            last_activity=Max('timestamp')
        ).order_by('-actions')[:20]

        # Store summary data
        instance.summary_data = {
            'total_actions': sum(activity['actions'] for activity in user_activity),
            'active_users': len(user_activity),
            'top_users': list(user_activity)[:5]
        }

        return True
    except Exception as e:
        logger.error(f'Error generating user activity report: {str(e)}', exc_info=True)
        return False


@shared_task
def send_report_email(instance_id):
    """
    Send report via email to configured recipients
    """
    try:
        from django.core.mail import EmailMessage
        from django.conf import settings

        instance = ReportInstance.objects.select_related('report').get(id=instance_id)

        if not instance.report.recipients:
            logger.info(f'No recipients configured for report instance {instance_id}')
            return True

        # Create email
        subject = f"FinSight Report: {instance.report.name}"
        body = f"""
Automated Report: {instance.report.name}

Report Period: {instance.start_date.date()} to {instance.end_date.date()}
Generated: {instance.completed_at.strftime('%Y-%m-%d %H:%M:%S')}

Summary:
{instance.summary_data}

This report was automatically generated by the FinSight system.
"""

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=instance.report.recipients
        )

        # Attach files
        if instance.pdf_file:
            email.attach_file(instance.pdf_file.path)
        if instance.excel_file:
            email.attach_file(instance.excel_file.path)
        if instance.csv_file and instance.report.include_raw_data:
            email.attach_file(instance.csv_file.path)

        # Send email
        email.send()

        # Mark as sent
        instance.sent_at = timezone.now()
        instance.save()

        logger.info(f'Successfully sent report email for instance {instance_id}')
        return True

    except Exception as e:
        logger.error(f'Error sending report email for instance {instance_id}: {str(e)}', exc_info=True)
        return False