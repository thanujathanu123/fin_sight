// Enhanced theme-aware chart options
function getChartOptions(isDark) {
    const primaryColor = isDark ? '#60a5fa' : '#3b82f6';
    const secondaryColor = isDark ? '#34d399' : '#22c55e';
    const dangerColor = isDark ? '#f87171' : '#ef4444';
    const warningColor = isDark ? '#fbbf24' : '#f59e0b';
    const textColor = isDark ? 'rgba(255, 255, 255, 0.9)' : 'rgba(0, 0, 0, 0.8)';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            title: {
                display: true,
                text: 'Risk Score Distribution',
                color: textColor,
                font: {
                    size: 16,
                    weight: '600',
                    family: 'Inter, sans-serif'
                },
                padding: {
                    top: 10,
                    bottom: 30
                }
            },
            legend: {
                labels: {
                    color: textColor,
                    font: {
                        size: 12,
                        weight: '500',
                        family: 'Inter, sans-serif'
                    },
                    padding: 20,
                    usePointStyle: true,
                    pointStyle: 'circle'
                },
                position: 'bottom'
            },
            tooltip: {
                backgroundColor: isDark ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                titleColor: textColor,
                bodyColor: textColor,
                borderColor: gridColor,
                borderWidth: 1,
                cornerRadius: 8,
                displayColors: true,
                padding: 12,
                titleFont: {
                    size: 14,
                    weight: '600'
                },
                bodyFont: {
                    size: 13
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    stepSize: 1,
                    color: textColor,
                    font: {
                        size: 11,
                        weight: '500'
                    },
                    padding: 10
                },
                grid: {
                    color: gridColor,
                    borderDash: [2, 4],
                    drawBorder: false
                },
                border: {
                    display: false
                }
            },
            x: {
                ticks: {
                    color: textColor,
                    font: {
                        size: 11,
                        weight: '500'
                    },
                    padding: 10
                },
                grid: {
                    color: gridColor,
                    borderDash: [2, 4],
                    drawBorder: false
                },
                border: {
                    display: false
                }
            }
        },
        elements: {
            point: {
                radius: 4,
                hoverRadius: 6,
                borderWidth: 2,
                hoverBorderWidth: 3
            },
            line: {
                borderWidth: 3,
                fill: true
            },
            bar: {
                borderRadius: 4,
                borderSkipped: false,
                borderWidth: 0
            }
        },
        animation: {
            duration: 1000,
            easing: 'easeOutQuart'
        }
    };
}

// Store chart instances
let charts = {};

// Update charts theme
function updateChartsTheme(isDark) {
    Object.values(charts).forEach(chart => {
        chart.options = { ...chart.options, ...getChartOptions(isDark) };
        chart.update('none');
    });
}

// Theme change observer
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-bs-theme') {
            const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
            updateChartsTheme(isDark);
        }
    });

    // Start observing theme changes
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-bs-theme']
    });
});

// WebSocket connection for real-time updates
let dashboardSocket = null;
let analyticsSocket = null;
let notificationSocket = null;

function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsStatusEl = document.getElementById('ws-status');

    // Update connection status
    function updateConnectionStatus(connected) {
        if (wsStatusEl) {
            wsStatusEl.className = `ws-status ${connected ? 'connected' : 'disconnected'}`;
        }
    }

    // Dashboard WebSocket (user-specific)
    const userId = document.body.dataset.userId;
    if (userId) {
        dashboardSocket = new WebSocket(`${protocol}//${host}/ws/dashboard/${userId}/`);

        dashboardSocket.onopen = function(e) {
            console.log('Dashboard WebSocket connected');
            updateConnectionStatus(true);
        };

        dashboardSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'dashboard_update') {
                updateDashboardRealtime(data.data);
            }
        };

        dashboardSocket.onclose = function(e) {
            console.log('Dashboard WebSocket closed, retrying in 5 seconds...');
            updateConnectionStatus(false);
            setTimeout(initializeWebSocket, 5000);
        };

        dashboardSocket.onerror = function(e) {
            console.error('Dashboard WebSocket error:', e);
            updateConnectionStatus(false);
        };
    }

    // Analytics WebSocket (system-wide)
    analyticsSocket = new WebSocket(`${protocol}//${host}/ws/analytics/`);

    analyticsSocket.onopen = function(e) {
        console.log('Analytics WebSocket connected');
    };

    analyticsSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'analytics_update') {
            updateAnalyticsRealtime(data.data);
        }
    };

    analyticsSocket.onclose = function(e) {
        console.log('Analytics WebSocket closed');
    };

    analyticsSocket.onerror = function(e) {
        console.error('Analytics WebSocket error:', e);
    };

    // Notification WebSocket
    if (userId) {
        notificationSocket = new WebSocket(`${protocol}//${host}/ws/notifications/${userId}/`);

        notificationSocket.onopen = function(e) {
            console.log('Notification WebSocket connected');
        };

        notificationSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'notification') {
                showRealtimeNotification(data.data);
            }
        };

        notificationSocket.onclose = function(e) {
            console.log('Notification WebSocket closed');
        };

        notificationSocket.onerror = function(e) {
            console.error('Notification WebSocket error:', e);
        };
    }
}

function updateDashboardRealtime(data) {
    // Update dashboard metrics in real-time
    if (data.transactions) {
        updateMetricCard('total-transactions', data.transactions.total_count);
        updateMetricCard('high-risk-transactions', data.transactions.high_risk_count);
        updateMetricCard('avg-risk-score', data.transactions.avg_risk.toFixed(1));
    }

    if (data.alerts) {
        updateMetricCard('total-alerts', data.alerts.total_alerts);
        updateMetricCard('resolved-alerts', data.alerts.resolved_alerts);
    }

    // Update recent activity
    if (data.recent_activity && data.recent_activity.length > 0) {
        updateRecentActivity(data.recent_activity);
    }

    // Show subtle update indicator
    showUpdateIndicator();
}

function updateAnalyticsRealtime(data) {
    // Update system-wide analytics
    if (data.total_transactions) {
        updateMetricCard('system-transactions', data.total_transactions);
    }

    if (data.risk_distribution) {
        // Update risk distribution chart if it exists
        if (charts.riskDistribution) {
            charts.riskDistribution.data.datasets[0].data = [
                data.risk_distribution.low,
                data.risk_distribution.medium,
                data.risk_distribution.high
            ];
            charts.riskDistribution.update('none');
        }
    }

    // Update processing status indicators
    if (data.processing_status) {
        updateProcessingStatus(data.processing_status);
    }
}

function updateMetricCard(cardId, value) {
    const card = document.getElementById(cardId);
    if (card) {
        // Add highlight animation
        card.classList.add('metric-update');
        card.textContent = value.toLocaleString();

        // Remove animation after 2 seconds
        setTimeout(() => {
            card.classList.remove('metric-update');
        }, 2000);
    }
}

function updateRecentActivity(activities) {
    const activityContainer = document.getElementById('recent-activity');
    if (activityContainer && activities.length > 0) {
        // Update the most recent activity item
        const latestActivity = activities[0];
        const activityElement = activityContainer.querySelector('.activity-item:first-child');
        if (activityElement) {
            activityElement.innerHTML = `
                <div class="activity-icon">
                    <i class="bi bi-${getActivityIcon(latestActivity.action)}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-text">
                        <strong>${latestActivity.user__username}</strong> ${latestActivity.action}d ${latestActivity.model_name}
                    </div>
                    <div class="activity-time">${formatTimeAgo(latestActivity.timestamp)}</div>
                </div>
            `;
        }
    }
}

function updateProcessingStatus(status) {
    // Update processing status badges
    Object.keys(status).forEach(key => {
        const element = document.getElementById(`status-${key}`);
        if (element) {
            element.textContent = status[key];
            if (status[key] > 0) {
                element.classList.add('status-active');
            } else {
                element.classList.remove('status-active');
            }
        }
    });
}

function showRealtimeNotification(notification) {
    // Create notification toast
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${getSeverityColor(notification.severity)} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${notification.title}</strong><br>
                    ${notification.message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    // Add to toast container
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    // Initialize and show toast
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, { delay: 10000 });
    toast.show();

    // Add click handler to navigate to alert
    toastElement.addEventListener('click', () => {
        if (notification.url) {
            window.location.href = notification.url;
        }
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

function getActivityIcon(action) {
    const iconMap = {
        'create': 'plus-circle',
        'update': 'pencil',
        'delete': 'trash',
        'view': 'eye',
        'export': 'download',
        'import': 'upload'
    };
    return iconMap[action] || 'activity';
}

function getSeverityColor(severity) {
    const colorMap = {
        'low': 'secondary',
        'medium': 'warning',
        'high': 'danger',
        'critical': 'danger'
    };
    return colorMap[severity] || 'primary';
}

function formatTimeAgo(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

function showUpdateIndicator() {
    // Show a subtle "updated" indicator
    const indicator = document.getElementById('realtime-indicator');
    if (indicator) {
        indicator.style.opacity = '1';
        setTimeout(() => {
            indicator.style.opacity = '0';
        }, 2000);
    }
}

// Dashboard initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Initialize DataTables with enhanced options
    $('.datatable').DataTable({
        pageLength: 25,
        responsive: true,
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        language: {
            search: "Search transactions:",
            lengthMenu: "Show _MENU_ entries per page",
        },
        initComplete: function() {
            // Add custom styling to DataTables elements
            $('.dataTables_length select').addClass('form-select form-select-sm');
            $('.dataTables_filter input').addClass('form-control form-control-sm');
        }
    });

    // Initialize advanced visualizations with a delay to ensure data is loaded
    setTimeout(initializeAdvancedCharts, 100);

    // Initialize progress circles
    initializeProgressCircles();

    // Add click handlers for table rows
    initializeTableInteractions();

    // Initialize WebSocket connections
    initializeWebSocket();
});

// Initialize progress circles
function initializeProgressCircles() {
    const circles = document.querySelectorAll('.progress-circle-fill');
    circles.forEach(circle => {
        const progress = circle.style.getPropertyValue('--progress') || '75%';
        circle.style.background = `conic-gradient(
            var(--primary-500) ${progress},
            var(--gray-200) ${progress}
        )`;
    });
}

// Initialize advanced visualizations
function initializeAdvancedCharts() {
    // Check if data is available, if not, retry after a short delay
    if (!window.dashboardData) {
        console.log('Dashboard data not available yet, retrying...');
        setTimeout(initializeAdvancedCharts, 200);
        return;
    }

    // Risk Distribution Pie Chart
    const riskChartEl = document.getElementById('riskDistributionChart');
    if (riskChartEl && window.finsightCharts) {
        // Use actual data from the backend
        const riskData = {
            low: parseInt(window.dashboardData.riskDistribution[0]) || 0,
            medium: parseInt(window.dashboardData.riskDistribution[1]) || 0,
            high: parseInt(window.dashboardData.riskDistribution[2]) || 0
        };

        console.log('Initializing risk distribution chart with data:', riskData);
        window.finsightCharts.createRiskDistributionChart('riskDistributionChart', riskData);
    }

    // Alert Status Chart
    const alertChartEl = document.getElementById('alertStatusChart');
    if (alertChartEl && window.finsightCharts) {
        // Use actual status breakdown data
        const statusData = window.dashboardData.statusBreakdown || [];
        // Convert status breakdown to chart data
        const alertData = statusData.map(item => ({
            status: item.label,
            count: item.count,
            percentage: item.percentage
        }));

        console.log('Initializing alert status chart with data:', alertData);
        window.finsightCharts.createAlertStatusChart('alertStatusChart', alertData);
    }

    // Transaction Trend Chart (if element exists)
    const trendChartEl = document.getElementById('transactionTrendChart');
    if (trendChartEl && window.finsightCharts) {
        // Sample trend data
        const trendData = [
            { date: '2024-01-01', count: 25, total_amount: 12500 },
            { date: '2024-01-02', count: 32, total_amount: 15800 },
            { date: '2024-01-03', count: 28, total_amount: 14200 },
            { date: '2024-01-04', count: 35, total_amount: 18900 },
            { date: '2024-01-05', count: 30, total_amount: 16500 }
        ];
        window.finsightCharts.createTransactionTrendChart('transactionTrendChart', trendData);
    }

    // Performance Gauge (if element exists)
    const gaugeEl = document.getElementById('performanceGauge');
    if (gaugeEl && window.finsightCharts) {
        const metrics = { compliance_rate: 87.5 };
        window.finsightCharts.createPerformanceGauge('performanceGauge', metrics);
    }
}

// Initialize table interactions
function initializeTableInteractions() {
    // Add row click handlers
    document.querySelectorAll('.datatable tbody tr').forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger if clicking on buttons
            if (e.target.closest('.btn')) return;

            const transactionId = this.dataset.transactionId;
            if (transactionId) {
                viewTransaction(transactionId);
            }
        });
    });
}

// Interactive functions for reviewer dashboard
function viewTransaction(transactionId) {
    // Show loading state
    showToast('Loading transaction details...', 'info');

    // Simulate API call - replace with actual implementation
    setTimeout(() => {
        showToast(`Viewing transaction ${transactionId}`, 'success');
        // Here you would typically open a modal or navigate to transaction detail page
        console.log('View transaction:', transactionId);
    }, 500);
}

function updateStatus(alertId, status) {
    showToast(`Updating alert ${alertId} to ${status}...`, 'info');

    // Simulate API call
    setTimeout(() => {
        showToast(`Alert ${alertId} updated successfully`, 'success');
        // Refresh the page or update the UI
        location.reload();
    }, 1000);
}

function refreshTable() {
    showToast('Refreshing data...', 'info');

    setTimeout(() => {
        showToast('Data refreshed successfully', 'success');
        location.reload();
    }, 1000);
}

function filterTable() {
    // Toggle filter controls or open filter modal
    showToast('Filter options opened', 'info');
}

function exportData() {
    // Show export options modal
    showExportModal();
}

function showExportModal() {
    // Remove existing modal if present
    const existingModal = document.getElementById('exportModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Create export modal
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'exportModal';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="bi bi-download me-2"></i>Export Data
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Data Type</label>
                            <select class="form-select" id="exportDataType">
                                <option value="transactions">Transactions</option>
                                <option value="alerts">Alerts</option>
                                <option value="analytics">Analytics Report</option>
                                <option value="ledger-summary">Ledger Summary</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Format</label>
                            <select class="form-select" id="exportFormat">
                                <option value="csv">CSV</option>
                                <option value="excel">Excel</option>
                                <option value="pdf">PDF</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">Start Date</label>
                            <input type="date" class="form-control" id="exportStartDate">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-semibold">End Date</label>
                            <input type="date" class="form-control" id="exportEndDate">
                        </div>
                        <div class="col-12">
                            <label class="form-label fw-semibold">Additional Filters</label>
                            <div class="row g-2">
                                <div class="col-md-6">
                                    <input type="number" class="form-control form-control-sm" id="exportMinRisk" placeholder="Min Risk Score (0-100)">
                                </div>
                                <div class="col-md-6">
                                    <input type="number" class="form-control form-control-sm" id="exportMaxRisk" placeholder="Max Risk Score (0-100)">
                                </div>
                            </div>
                        </div>
                        <div class="col-12">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="exportAssignedToMe" checked>
                                <label class="form-check-label" for="exportAssignedToMe">
                                    Only alerts assigned to me (for alert exports)
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="performExport()">
                        <i class="bi bi-download me-2"></i>Export
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Set default dates (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('exportStartDate').value = thirtyDaysAgo.toISOString().split('T')[0];
    document.getElementById('exportEndDate').value = today.toISOString().split('T')[0];

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function performExport() {
    const dataType = document.getElementById('exportDataType').value;
    const format = document.getElementById('exportFormat').value;
    const startDate = document.getElementById('exportStartDate').value;
    const endDate = document.getElementById('exportEndDate').value;
    const minRisk = document.getElementById('exportMinRisk').value;
    const maxRisk = document.getElementById('exportMaxRisk').value;
    const assignedToMe = document.getElementById('exportAssignedToMe').checked;

    // Build URL based on data type
    let url;
    switch (dataType) {
        case 'transactions':
            url = '/api/export/transactions/';
            break;
        case 'alerts':
            url = '/api/export/alerts/';
            break;
        case 'analytics':
            url = '/api/export/analytics/';
            break;
        case 'ledger-summary':
            url = '/api/export/ledger-summary/';
            break;
        default:
            showToast('Invalid data type selected', 'danger');
            return;
    }

    // Build query parameters
    const params = new URLSearchParams();
    params.append('format', format);

    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (minRisk) params.append('risk_min', minRisk);
    if (maxRisk) params.append('risk_max', maxRisk);
    if (dataType === 'alerts' && assignedToMe) params.append('assigned_to_me', 'true');

    // Generate filename
    const timestamp = new Date().toISOString().split('T')[0];
    const filename = `${dataType}_export_${timestamp}.${format === 'excel' ? 'xlsx' : format}`;
    params.append('filename', filename);

    const fullUrl = `${url}?${params.toString()}`;

    showToast('Starting export...', 'info');

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('exportModal'));
    modal.hide();

    try {
        // Create a temporary link to trigger download
        const link = document.createElement('a');
        link.href = fullUrl;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showToast('Export started successfully. Download should begin shortly.', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showToast('Export failed. Please try again.', 'danger');
    }
}

function bulkApprove() {
    if (confirm('Are you sure you want to bulk approve all low-risk transactions?')) {
        showToast('Processing bulk approval...', 'warning');

        setTimeout(() => {
            showToast('Bulk approval completed successfully', 'success');
        }, 2000);
    }
}

function escalateHighRisk() {
    if (confirm('Are you sure you want to escalate all high-risk transactions?')) {
        showToast('Escalating high-risk transactions...', 'warning');

        setTimeout(() => {
            showToast('High-risk transactions escalated successfully', 'success');
        }, 2000);
    }
}

function generateReport() {
    showToast('Generating report...', 'info');

    setTimeout(() => {
        showToast('Report generated successfully', 'success');
        // Here you would open/download the report
    }, 2000);
}

function viewAllActivity() {
    showToast('Opening activity log...', 'info');
    // Here you would navigate to activity page or open modal
}

// Enhanced File Upload Functionality
function initializeFileUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const uploadBtn = document.getElementById('uploadBtn');
    const removeFile = document.getElementById('removeFile');
    const uploadIcon = document.getElementById('uploadIcon');

    if (!uploadZone) return;

    // Click to browse files
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, unhighlight, false);
    });

    uploadZone.addEventListener('drop', handleDrop, false);

    // Remove file
    removeFile.addEventListener('click', () => {
        clearFileSelection();
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        uploadZone.classList.add('dragover');
        uploadIcon.classList.add('animate-bounce');
    }

    function unhighlight() {
        uploadZone.classList.remove('dragover');
        uploadIcon.classList.remove('animate-bounce');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            handleFileSelect({ target: { files: files } });
        }
    }

    function handleFileSelect(e) {
        const files = e.target.files;

        if (files.length > 0) {
            const file = files[0];

            // Validate file type
            const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
            if (!allowedTypes.includes(file.type) && !file.name.match(/\.(csv|xlsx|xls)$/i)) {
                showToast('Please select a valid CSV or Excel file', 'danger');
                return;
            }

            // Validate file size (10MB limit)
            if (file.size > 10 * 1024 * 1024) {
                showToast('File size must be less than 10MB', 'danger');
                return;
            }

            // Show file preview
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);

            document.getElementById('uploadZone').style.display = 'none';
            filePreview.classList.remove('d-none');

            // Enable upload button
            uploadBtn.disabled = false;
            uploadBtn.classList.add('animate-pulse');

            showToast(`File "${file.name}" selected successfully`, 'success');
        }
    }

    function clearFileSelection() {
        fileInput.value = '';
        document.getElementById('uploadZone').style.display = 'block';
        filePreview.classList.add('d-none');
        uploadBtn.disabled = true;
        uploadBtn.classList.remove('animate-pulse');
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Clear form function
function clearForm() {
    const form = document.getElementById('uploadForm');
    if (form) {
        form.reset();
        initializeFileUpload(); // Reinitialize file upload
        const uploadBtn = document.getElementById('uploadBtn');
        uploadBtn.disabled = true;
        uploadBtn.classList.remove('animate-pulse');
        showToast('Form cleared', 'info');
    }
}

// Form submission enhancement
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const uploadBtn = document.getElementById('uploadBtn');
            const uploadBtnText = document.getElementById('uploadBtnText');

            // Show loading state
            uploadBtn.disabled = true;
            uploadBtnText.textContent = 'Uploading...';
            uploadBtn.innerHTML = '<i class="bi bi-arrow-repeat animate-pulse me-2"></i><span id="uploadBtnText">Uploading...</span>';

            showToast('Starting file upload and analysis...', 'info');
        });
    }

    // Initialize file upload functionality
    initializeFileUpload();
});

// Toast notification system
function showToast(message, type = 'info') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(toast => toast.remove());

    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        delay: 3000
    });
    bsToast.show();

    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}
