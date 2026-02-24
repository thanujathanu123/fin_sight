from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Transaction, Alert, LedgerUpload, AuditLog, Report, ReportInstance
from .exports import TransactionExporter, AlertExporter, AnalyticsReportExporter
from .permissions import IsInGroup
from .tasks import generate_report_instance
from .predictive_analytics import PredictiveAnalyticsEngine, RiskPredictor


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_transactions(request):
    """
    Export transactions in various formats (CSV, Excel, PDF)
    Query parameters:
    - format: csv, excel, pdf (default: csv)
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - risk_min: minimum risk score
    - risk_max: maximum risk score
    - status: transaction status
    - filename: custom filename
    """
    # Parse query parameters
    export_format = request.GET.get('format', 'csv').lower()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    risk_min = request.GET.get('risk_min')
    risk_max = request.GET.get('risk_max')
    transaction_status = request.GET.get('status')
    filename = request.GET.get('filename')

    # Build queryset
    queryset = Transaction.objects.select_related('ledger_upload', 'reviewed_by')

    # Apply filters
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            queryset = queryset.filter(date__gte=start_date)
        except ValueError:
            return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
            queryset = queryset.filter(date__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if risk_min:
        try:
            queryset = queryset.filter(risk_score__gte=float(risk_min))
        except ValueError:
            return Response({'error': 'Invalid risk_min value'}, status=status.HTTP_400_BAD_REQUEST)

    if risk_max:
        try:
            queryset = queryset.filter(risk_score__lte=float(risk_max))
        except ValueError:
            return Response({'error': 'Invalid risk_max value'}, status=status.HTTP_400_BAD_REQUEST)

    if transaction_status:
        queryset = queryset.filter(status=transaction_status)

    # Apply role-based filtering
    user = request.user
    if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
        # Non-admin users can only see transactions from their uploads
        queryset = queryset.filter(ledger_upload__uploaded_by=user)

    # Limit results for performance
    queryset = queryset.order_by('-date')[:10000]  # Max 10k records

    # Export based on format
    try:
        if export_format == 'excel':
            return TransactionExporter.export_excel(queryset, filename)
        elif export_format == 'pdf':
            return TransactionExporter.export_pdf(queryset, filename)
        else:  # default to csv
            return TransactionExporter.export_csv(queryset, filename)
    except Exception as e:
        return Response({'error': f'Export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_alerts(request):
    """
    Export alerts in various formats (CSV, Excel, PDF)
    Query parameters:
    - format: csv, excel, pdf (default: csv)
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - severity: alert severity
    - status: alert status
    - assigned_to_me: true/false (only alerts assigned to current user)
    - filename: custom filename
    """
    export_format = request.GET.get('format', 'csv').lower()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    severity = request.GET.get('severity')
    alert_status = request.GET.get('status')
    assigned_to_me = request.GET.get('assigned_to_me', '').lower() == 'true'
    filename = request.GET.get('filename')

    # Build queryset
    queryset = Alert.objects.select_related('transaction', 'created_by', 'assigned_to')

    # Apply filters
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            queryset = queryset.filter(created_at__gte=start_date)
        except ValueError:
            return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
            queryset = queryset.filter(created_at__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if severity:
        queryset = queryset.filter(severity=severity)

    if alert_status:
        queryset = queryset.filter(status=alert_status)

    if assigned_to_me:
        queryset = queryset.filter(assigned_to=request.user)

    # Apply role-based filtering
    user = request.user
    if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
        # Non-admin users can only see alerts assigned to them or created by them
        queryset = queryset.filter(Q(assigned_to=user) | Q(created_by=user))

    queryset = queryset.order_by('-created_at')[:5000]  # Max 5k records

    try:
        if export_format == 'excel':
            return AlertExporter.export_excel(queryset, filename)
        elif export_format == 'pdf':
            return AlertExporter.export_pdf(queryset, filename)
        else:
            return AlertExporter.export_csv(queryset, filename)
    except Exception as e:
        return Response({'error': f'Export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInGroup])
def export_analytics_report(request):
    """
    Export analytics summary report as PDF
    Query parameters:
    - start_date: YYYY-MM-DD (default: 30 days ago)
    - end_date: YYYY-MM-DD (default: today)
    - filename: custom filename
    """
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    filename = request.GET.get('filename')

    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
        except ValueError:
            return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
        except ValueError:
            return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        return AnalyticsReportExporter.export_summary_pdf(start_date, end_date, filename)
    except Exception as e:
        return Response({'error': f'Report generation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_audit_log(request):
    """
    Export audit log entries
    Query parameters:
    - format: csv, excel (default: csv)
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - action: specific action type
    - user: username
    - model_name: model affected
    - filename: custom filename
    """
    export_format = request.GET.get('format', 'csv').lower()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    action = request.GET.get('action')
    username = request.GET.get('user')
    model_name = request.GET.get('model_name')
    filename = request.GET.get('filename')

    # Only admins can access audit logs
    if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    queryset = AuditLog.objects.select_related('user')

    # Apply filters
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            queryset = queryset.filter(timestamp__gte=start_date)
        except ValueError:
            return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
            queryset = queryset.filter(timestamp__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if action:
        queryset = queryset.filter(action=action)

    if username:
        queryset = queryset.filter(user__username=username)

    if model_name:
        queryset = queryset.filter(model_name=model_name)

    queryset = queryset.order_by('-timestamp')[:10000]  # Max 10k records

    fields = ['timestamp', 'user__username', 'action', 'model_name', 'object_id', 'object_repr', 'ip_address']

    try:
        from .exports import CSVExporter, ExcelExporter

        if export_format == 'excel':
            exporter = ExcelExporter(queryset, fields)
            return exporter.export(filename or 'audit_log.xlsx', 'Audit Log')
        else:
            exporter = CSVExporter(queryset, fields)
            return exporter.export(filename or 'audit_log.csv')
    except Exception as e:
        return Response({'error': f'Export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_ledger_summary(request):
    """
    Export ledger upload summary
    Query parameters:
    - format: csv, excel (default: csv)
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - status: upload status
    - filename: custom filename
    """
    export_format = request.GET.get('format', 'csv').lower()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    upload_status = request.GET.get('status')
    filename = request.GET.get('filename')

    queryset = LedgerUpload.objects.select_related('uploaded_by', 'risk_profile')

    # Apply role-based filtering
    user = request.user
    if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
        queryset = queryset.filter(uploaded_by=user)

    # Apply filters
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str)
            queryset = queryset.filter(uploaded_at__gte=start_date)
        except ValueError:
            return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str)
            queryset = queryset.filter(uploaded_at__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid end_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    if upload_status:
        queryset = queryset.filter(status=upload_status)

    queryset = queryset.order_by('-uploaded_at')[:5000]  # Max 5k records

    fields = ['filename', 'uploaded_at', 'uploaded_by__username', 'status', 'risk_score',
             'transaction_count', 'high_risk_count', 'processing_time', 'risk_profile__name']

    try:
        from .exports import CSVExporter, ExcelExporter

        if export_format == 'excel':
            exporter = ExcelExporter(queryset, fields)
            return exporter.export(filename or 'ledger_summary.xlsx', 'Ledger Summary')
        else:
            exporter = CSVExporter(queryset, fields)
            return exporter.export(filename or 'ledger_summary.csv')
    except Exception as e:
        return Response({'error': f'Export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsInGroup])
def reports_list(request):
    """
    List all reports or create a new report
    """
    if request.method == 'GET':
        # Only show reports created by the user or if user is admin
        if request.user.groups.filter(name__in=['Admin', 'Auditor']).exists():
            reports = Report.objects.all()
        else:
            reports = Report.objects.filter(created_by=request.user)

        reports_data = []
        for report in reports:
            reports_data.append({
                'id': report.id,
                'name': report.name,
                'description': report.description,
                'report_type': report.report_type,
                'frequency': report.frequency,
                'is_active': report.is_active,
                'last_run': report.last_run,
                'next_run': report.next_run,
                'recipients': report.recipients,
                'created_at': report.created_at,
                'instances_count': report.instances.count()
            })

        return Response(reports_data)

    elif request.method == 'POST':
        # Create new report
        data = request.data
        try:
            report = Report.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                report_type=data['report_type'],
                frequency=data['frequency'],
                date_range_days=data.get('date_range_days', 30),
                include_charts=data.get('include_charts', True),
                include_raw_data=data.get('include_raw_data', False),
                recipients=data.get('recipients', []),
                risk_threshold_min=data.get('risk_threshold_min'),
                risk_threshold_max=data.get('risk_threshold_max'),
                include_high_risk_only=data.get('include_high_risk_only', False),
                created_by=request.user
            )

            # Calculate next run time
            report.calculate_next_run()
            report.save()

            return Response({
                'id': report.id,
                'message': 'Report created successfully'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Failed to create report: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def report_detail(request, report_id):
    """
    Get, update, or delete a specific report
    """
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check permissions
    if not (request.user.is_superuser or
            request.user.groups.filter(name__in=['Admin', 'Auditor']).exists() or
            report.created_by == request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response({
            'id': report.id,
            'name': report.name,
            'description': report.description,
            'report_type': report.report_type,
            'frequency': report.frequency,
            'date_range_days': report.date_range_days,
            'include_charts': report.include_charts,
            'include_raw_data': report.include_raw_data,
            'recipients': report.recipients,
            'risk_threshold_min': report.risk_threshold_min,
            'risk_threshold_max': report.risk_threshold_max,
            'include_high_risk_only': report.include_high_risk_only,
            'is_active': report.is_active,
            'last_run': report.last_run,
            'next_run': report.next_run,
            'created_at': report.created_at,
            'updated_at': report.updated_at
        })

    elif request.method == 'PUT':
        data = request.data
        try:
            report.name = data.get('name', report.name)
            report.description = data.get('description', report.description)
            report.report_type = data.get('report_type', report.report_type)
            report.frequency = data.get('frequency', report.frequency)
            report.date_range_days = data.get('date_range_days', report.date_range_days)
            report.include_charts = data.get('include_charts', report.include_charts)
            report.include_raw_data = data.get('include_raw_data', report.include_raw_data)
            report.recipients = data.get('recipients', report.recipients)
            report.risk_threshold_min = data.get('risk_threshold_min', report.risk_threshold_min)
            report.risk_threshold_max = data.get('risk_threshold_max', report.risk_threshold_max)
            report.include_high_risk_only = data.get('include_high_risk_only', report.include_high_risk_only)
            report.is_active = data.get('is_active', report.is_active)

            report.save()

            # Recalculate next run if frequency changed
            if 'frequency' in data:
                report.calculate_next_run()
                report.save()

            return Response({'message': 'Report updated successfully'})

        except Exception as e:
            return Response({'error': f'Failed to update report: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        report.delete()
        return Response({'message': 'Report deleted successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report_now(request, report_id):
    """
    Manually trigger report generation
    """
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check permissions
    if not (request.user.is_superuser or
            request.user.groups.filter(name__in=['Admin', 'Auditor']).exists() or
            report.created_by == request.user):
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Trigger report generation
        generate_report_instance.delay(report_id)
        return Response({'message': 'Report generation started successfully'})
    except Exception as e:
        return Response({'error': f'Failed to start report generation: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_instances(request, report_id=None):
    """
    List report instances for a specific report or all reports
    """
    if report_id:
        # Check permissions for specific report
        try:
            report = Report.objects.get(id=report_id)
            if not (request.user.is_superuser or
                    request.user.groups.filter(name__in=['Admin', 'Auditor']).exists() or
                    report.created_by == request.user):
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
            instances = ReportInstance.objects.filter(report=report)
        except Report.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Show instances for user's reports or all if admin
        if request.user.groups.filter(name__in=['Admin', 'Auditor']).exists():
            instances = ReportInstance.objects.all()
        else:
            instances = ReportInstance.objects.filter(report__created_by=request.user)

    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        instances = instances.filter(status=status_filter)

    start_date = request.GET.get('start_date')
    if start_date:
        try:
            start_date = datetime.fromisoformat(start_date)
            instances = instances.filter(created_at__gte=start_date)
        except ValueError:
            return Response({'error': 'Invalid start_date format'}, status=status.HTTP_400_BAD_REQUEST)

    end_date = request.GET.get('end_date')
    if end_date:
        try:
            end_date = datetime.fromisoformat(end_date)
            instances = instances.filter(created_at__lte=end_date)
        except ValueError:
            return Response({'error': 'Invalid end_date format'}, status=status.HTTP_400_BAD_REQUEST)

    instances = instances.order_by('-created_at')[:100]  # Limit to 100 most recent

    instances_data = []
    for instance in instances:
        instances_data.append({
            'id': instance.id,
            'report_name': instance.report.name,
            'status': instance.status,
            'start_date': instance.start_date,
            'end_date': instance.end_date,
            'created_at': instance.created_at,
            'completed_at': instance.completed_at,
            'sent_at': instance.sent_at,
            'summary_data': instance.summary_data,
            'error_message': instance.error_message,
            'file_urls': instance.get_file_urls()
        })

    return Response(instances_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_types(request):
    """
    Get available report types and their configurations
    """
    report_types_data = {
        'transaction_summary': {
            'name': 'Transaction Summary',
            'description': 'Comprehensive summary of all transactions with risk analysis',
            'available_filters': ['date_range', 'risk_threshold', 'high_risk_only']
        },
        'risk_analysis': {
            'name': 'Risk Analysis Report',
            'description': 'Detailed analysis of high-risk transactions and patterns',
            'available_filters': ['date_range', 'risk_distribution']
        },
        'alert_summary': {
            'name': 'Alert Summary',
            'description': 'Summary of all alerts and their resolution status',
            'available_filters': ['date_range', 'severity', 'status']
        },
        'compliance_report': {
            'name': 'Compliance Report',
            'description': 'Compliance metrics and review coverage analysis',
            'available_filters': ['date_range']
        },
        'user_activity': {
            'name': 'User Activity Report',
            'description': 'User activity and system usage statistics',
            'available_filters': ['date_range']
        }
    }

    return Response(report_types_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInGroup])
def risk_forecast(request):
    """
    Generate risk forecast and predictive analytics
    Query parameters:
    - days: forecast period in days (default: 30)
    - include_trends: include trend analysis (default: true)
    - include_anomalies: include anomaly detection (default: true)
    """
    forecast_days = int(request.GET.get('days', 30))
    include_trends = request.GET.get('include_trends', 'true').lower() == 'true'
    include_anomalies = request.GET.get('include_anomalies', 'true').lower() == 'true'

    try:
        # Get historical transaction data
        end_date = timezone.now()
        start_date = end_date - timedelta(days=90)  # 90 days of historical data

        transactions = Transaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('id', 'date', 'amount', 'risk_score')

        # Apply role-based filtering
        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
            # Non-admin users can only see their own data
            ledger_ids = LedgerUpload.objects.filter(uploaded_by=user).values_list('id', flat=True)
            transactions = transactions.filter(ledger_upload_id__in=ledger_ids)

        transaction_list = list(transactions)

        if not transaction_list:
            return Response({'error': 'Insufficient historical data for forecasting'}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize predictive analytics engine
        engine = PredictiveAnalyticsEngine()

        # Prepare time series data
        ts_data = engine.prepare_time_series_data(transaction_list)

        if ts_data.empty:
            return Response({'error': 'Unable to prepare data for analysis'}, status=status.HTTP_400_BAD_REQUEST)

        # Train models (in production, this would be done periodically)
        engine.train_predictive_models(ts_data)

        # Generate forecast
        forecast = engine.generate_risk_forecast(ts_data, forecast_days)

        # Optionally remove detailed trend analysis for performance
        if not include_trends and 'trend_analysis' in forecast:
            del forecast['trend_analysis']

        return Response(forecast)

    except Exception as e:
        return Response({'error': f'Forecast generation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_transaction_risk(request):
    """
    Predict risk score for a single transaction
    Request body:
    {
        "amount": 1500.00,
        "hour": 14,
        "day_of_week": 1,
        "description": "Optional transaction description"
    }
    """
    try:
        data = request.data
        amount = float(data.get('amount', 0))
        hour = int(data.get('hour', 12))
        day_of_week = int(data.get('day_of_week', 0))

        if amount <= 0:
            return Response({'error': 'Invalid transaction amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Get historical context for the user
        user = request.user
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        historical_transactions = Transaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('date', 'amount', 'risk_score')

        # Apply role-based filtering
        if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
            ledger_ids = LedgerUpload.objects.filter(uploaded_by=user).values_list('id', flat=True)
            historical_transactions = historical_transactions.filter(ledger_upload_id__in=ledger_ids)

        historical_list = list(historical_transactions)

        # Prepare transaction data
        transaction_data = {
            'amount': amount,
            'hour': hour,
            'day_of_week': day_of_week,
            'description': data.get('description', '')
        }

        # Initialize risk predictor
        predictor = RiskPredictor()

        # Generate prediction
        prediction = predictor.predict_transaction_risk(transaction_data, historical_list)

        return Response(prediction)

    except ValueError as e:
        return Response({'error': 'Invalid input data format'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Risk prediction failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInGroup])
def trend_analysis(request):
    """
    Perform trend analysis on transaction data
    Query parameters:
    - start_date: analysis start date (default: 90 days ago)
    - end_date: analysis end date (default: today)
    - metrics: comma-separated list of metrics to analyze
    """
    try:
        # Parse date parameters
        end_date = timezone.now()
        start_date_str = request.GET.get('start_date')
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        else:
            start_date = end_date - timedelta(days=90)

        metrics = request.GET.get('metrics', 'transaction_count,total_amount,avg_risk').split(',')

        # Get transaction data
        transactions = Transaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('id', 'date', 'amount', 'risk_score')

        # Apply role-based filtering
        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
            ledger_ids = LedgerUpload.objects.filter(uploaded_by=user).values_list('id', flat=True)
            transactions = transactions.filter(ledger_upload_id__in=ledger_ids)

        transaction_list = list(transactions)

        if not transaction_list:
            return Response({'error': 'No transaction data available for analysis'}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize analytics engine
        engine = PredictiveAnalyticsEngine()

        # Prepare time series data
        ts_data = engine.prepare_time_series_data(transaction_list)

        if ts_data.empty:
            return Response({'error': 'Unable to prepare data for analysis'}, status=status.HTTP_400_BAD_REQUEST)

        # Perform trend analysis
        trends = engine.analyze_trends(ts_data)

        # Filter to requested metrics
        filtered_trends = {}
        for key, value in trends.items():
            metric_name = key.split('_')[0] if '_' in key else key
            if metric_name in metrics or key in ['anomalies']:
                filtered_trends[key] = value

        return Response({
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'trends': filtered_trends,
            'data_points': len(ts_data),
            'generated_at': timezone.now().isoformat()
        })

    except Exception as e:
        return Response({'error': f'Trend analysis failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsInGroup])
def anomaly_detection(request):
    """
    Detect anomalies in transaction patterns
    Query parameters:
    - start_date: analysis start date (default: 30 days ago)
    - end_date: analysis end date (default: today)
    - threshold: anomaly detection threshold (default: 2.0)
    """
    try:
        # Parse parameters
        end_date = timezone.now()
        start_date_str = request.GET.get('start_date')
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        else:
            start_date = end_date - timedelta(days=30)

        threshold = float(request.GET.get('threshold', 2.0))

        # Get transaction data
        transactions = Transaction.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).values('id', 'date', 'amount', 'risk_score')

        # Apply role-based filtering
        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=['Admin', 'Auditor']).exists()):
            ledger_ids = LedgerUpload.objects.filter(uploaded_by=user).values_list('id', flat=True)
            transactions = transactions.filter(ledger_upload_id__in=ledger_ids)

        transaction_list = list(transactions)

        if len(transaction_list) < 14:
            return Response({'error': 'Insufficient data for anomaly detection (minimum 14 days required)'}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize analytics engine
        engine = PredictiveAnalyticsEngine()

        # Prepare time series data
        ts_data = engine.prepare_time_series_data(transaction_list)

        if ts_data.empty:
            return Response({'error': 'Unable to prepare data for analysis'}, status=status.HTTP_400_BAD_REQUEST)

        # Detect anomalies
        anomalies = engine._detect_anomalies(ts_data)

        # Group anomalies by severity
        high_severity = [a for a in anomalies if a.get('severity', 'medium') == 'high']
        medium_severity = [a for a in anomalies if a.get('severity', 'medium') == 'medium']
        low_severity = [a for a in anomalies if a.get('severity', 'medium') == 'low']

        return Response({
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'anomaly_summary': {
                'total_anomalies': len(anomalies),
                'high_severity': len(high_severity),
                'medium_severity': len(medium_severity),
                'low_severity': len(low_severity),
                'threshold_used': threshold
            },
            'anomalies': anomalies[:50],  # Limit to 50 most recent
            'data_points_analyzed': len(ts_data),
            'generated_at': timezone.now().isoformat()
        })

    except Exception as e:
        return Response({'error': f'Anomaly detection failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)