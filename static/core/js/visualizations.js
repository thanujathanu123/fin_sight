// Advanced Data Visualization Library
class FinSightCharts {
    constructor() {
        this.charts = {};
        this.themes = {
            light: {
                primary: '#3b82f6',
                secondary: '#22c55e',
                danger: '#ef4444',
                warning: '#f59e0b',
                success: '#22c55e',
                background: 'rgba(255, 255, 255, 0.9)',
                text: 'rgba(0, 0, 0, 0.8)',
                grid: 'rgba(0, 0, 0, 0.1)'
            },
            dark: {
                primary: '#60a5fa',
                secondary: '#34d399',
                danger: '#f87171',
                warning: '#fbbf24',
                success: '#34d399',
                background: 'rgba(31, 41, 55, 0.9)',
                text: 'rgba(255, 255, 255, 0.9)',
                grid: 'rgba(255, 255, 255, 0.1)'
            }
        };
    }

    getCurrentTheme() {
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        return isDark ? this.themes.dark : this.themes.light;
    }

    // Risk Distribution Pie Chart
    createRiskDistributionChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error('Canvas element not found:', canvasId);
            return null;
        }

        console.log('Creating risk distribution chart for', canvasId, 'with data:', data);
        const theme = this.getCurrentTheme();

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                datasets: [{
                    data: [data.low || 0, data.medium || 0, data.high || 0],
                    backgroundColor: [
                        theme.secondary,
                        theme.warning,
                        theme.danger
                    ],
                    borderColor: [
                        theme.secondary,
                        theme.warning,
                        theme.danger
                    ],
                    borderWidth: 2,
                    hoverBorderWidth: 4,
                    hoverBorderColor: [
                        theme.secondary,
                        theme.warning,
                        theme.danger
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: theme.text,
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateScale: true,
                    animateRotate: true,
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        console.log('Risk distribution chart created successfully for', canvasId);
        this.charts[canvasId] = chart;
        return chart;
    }

    // Transaction Trend Line Chart
    createTransactionTrendChart(canvasId, trendData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const theme = this.getCurrentTheme();

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trendData.map(item => new Date(item.date).toLocaleDateString()),
                datasets: [{
                    label: 'Transaction Count',
                    data: trendData.map(item => item.count),
                    borderColor: theme.primary,
                    backgroundColor: theme.primary + '20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: theme.primary,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: theme.primary,
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 3
                }, {
                    label: 'Total Amount ($)',
                    data: trendData.map(item => item.total_amount),
                    borderColor: theme.secondary,
                    backgroundColor: theme.secondary + '20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: theme.secondary,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: theme.secondary,
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 3,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            color: theme.text,
                            usePointStyle: true,
                            pointStyle: 'line'
                        }
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                if (context.datasetIndex === 1) {
                                    return `${context.dataset.label}: $${context.parsed.y.toLocaleString()}`;
                                }
                                return `${context.dataset.label}: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date',
                            color: theme.text
                        },
                        ticks: {
                            color: theme.text
                        },
                        grid: {
                            color: theme.grid
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Transaction Count',
                            color: theme.text
                        },
                        ticks: {
                            color: theme.text,
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        },
                        grid: {
                            color: theme.grid
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Total Amount ($)',
                            color: theme.text
                        },
                        ticks: {
                            color: theme.text,
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: {
                            drawOnChartArea: false,
                            color: theme.grid
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    // Risk Score Heatmap
    createRiskHeatmap(canvasId, heatmapData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const theme = this.getCurrentTheme();

        // Prepare data for heatmap
        const labels = [];
        const datasets = [];

        // Group data by hour and day of week
        const hourlyData = Array(7).fill().map(() => Array(24).fill(0));
        const hourlyCounts = Array(7).fill().map(() => Array(24).fill(0));

        heatmapData.forEach(item => {
            const date = new Date(item.date);
            const dayOfWeek = date.getDay();
            const hour = date.getHours();
            hourlyData[dayOfWeek][hour] += item.risk_score;
            hourlyCounts[dayOfWeek][hour] += 1;
        });

        // Calculate averages
        const avgData = hourlyData.map((day, dayIndex) =>
            day.map((total, hourIndex) => {
                const count = hourlyCounts[dayIndex][hourIndex];
                return count > 0 ? total / count : 0;
            })
        );

        const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const hourLabels = Array.from({length: 24}, (_, i) => `${i}:00`);

        datasets.push({
            label: 'Average Risk Score',
            data: avgData.flat(),
            backgroundColor: function(context) {
                const value = context.parsed.y;
                if (value >= 70) return theme.danger + '80';
                if (value >= 40) return theme.warning + '80';
                return theme.secondary + '80';
            },
            borderColor: function(context) {
                const value = context.parsed.y;
                if (value >= 70) return theme.danger;
                if (value >= 40) return theme.warning;
                return theme.secondary;
            },
            borderWidth: 1,
            borderRadius: 4,
            borderSkipped: false
        });

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dayNames.flatMap(day => hourLabels.map(hour => `${day} ${hour}`)),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            title: function(context) {
                                const label = context[0].label;
                                return label;
                            },
                            label: function(context) {
                                return `Avg Risk Score: ${context.parsed.y.toFixed(1)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: false // Hide x-axis for heatmap effect
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: theme.text,
                            callback: function(value) {
                                return value;
                            }
                        },
                        grid: {
                            color: theme.grid
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    // Alert Severity Timeline
    createAlertTimelineChart(canvasId, alertData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const theme = this.getCurrentTheme();

        // Group alerts by date and severity
        const dateMap = new Map();

        alertData.forEach(alert => {
            const date = new Date(alert.created_at).toISOString().split('T')[0];
            if (!dateMap.has(date)) {
                dateMap.set(date, { low: 0, medium: 0, high: 0, critical: 0 });
            }
            const severity = alert.severity.toLowerCase();
            if (dateMap.get(date)[severity] !== undefined) {
                dateMap.get(date)[severity]++;
            }
        });

        const dates = Array.from(dateMap.keys()).sort();
        const lowData = dates.map(date => dateMap.get(date).low);
        const mediumData = dates.map(date => dateMap.get(date).medium);
        const highData = dates.map(date => dateMap.get(date).high);
        const criticalData = dates.map(date => dateMap.get(date).critical);

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates.map(date => new Date(date).toLocaleDateString()),
                datasets: [{
                    label: 'Critical',
                    data: criticalData,
                    backgroundColor: theme.danger + '90',
                    borderColor: theme.danger,
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                    stack: 'alerts'
                }, {
                    label: 'High',
                    data: highData,
                    backgroundColor: theme.danger + '70',
                    borderColor: theme.danger,
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                    stack: 'alerts'
                }, {
                    label: 'Medium',
                    data: mediumData,
                    backgroundColor: theme.warning + '70',
                    borderColor: theme.warning,
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                    stack: 'alerts'
                }, {
                    label: 'Low',
                    data: lowData,
                    backgroundColor: theme.secondary + '70',
                    borderColor: theme.secondary,
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                    stack: 'alerts'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: theme.text,
                            usePointStyle: true,
                            pointStyle: 'rect'
                        }
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        cornerRadius: 8,
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        ticks: {
                            color: theme.text
                        },
                        grid: {
                            color: theme.grid
                        }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: {
                            color: theme.text,
                            stepSize: 1
                        },
                        grid: {
                            color: theme.grid
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    // Performance Metrics Gauge
    createPerformanceGauge(canvasId, metrics) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const theme = this.getCurrentTheme();

        // Create gauge chart using doughnut
        const value = metrics.compliance_rate || 0;
        const remaining = 100 - value;

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [value, remaining],
                    backgroundColor: [
                        value >= 80 ? theme.success : value >= 60 ? theme.warning : theme.danger,
                        theme.grid
                    ],
                    borderWidth: 0,
                    cutout: '70%',
                    circumference: 270,
                    rotation: 225
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    },
                    title: {
                        display: true,
                        text: `${value.toFixed(1)}%`,
                        color: theme.text,
                        font: {
                            size: 24,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 20
                        }
                    },
                    subtitle: {
                        display: true,
                        text: 'Compliance Rate',
                        color: theme.text,
                        font: {
                            size: 14
                        },
                        padding: {
                            top: 10
                        }
                    }
                },
                animation: {
                    animateScale: true,
                    animateRotate: true,
                    duration: 1500,
                    easing: 'easeOutQuart'
                }
            }
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    // Update theme for all charts
    updateTheme() {
        const theme = this.getCurrentTheme();
        Object.values(this.charts).forEach(chart => {
            if (chart.options.plugins) {
                if (chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                    chart.options.plugins.legend.labels.color = theme.text;
                }
                if (chart.options.plugins.tooltip) {
                    chart.options.plugins.tooltip.backgroundColor = theme.background;
                    chart.options.plugins.tooltip.titleColor = theme.text;
                    chart.options.plugins.tooltip.bodyColor = theme.text;
                    chart.options.plugins.tooltip.borderColor = theme.grid;
                }
                if (chart.options.plugins.title) {
                    chart.options.plugins.title.color = theme.text;
                }
                if (chart.options.plugins.subtitle) {
                    chart.options.plugins.subtitle.color = theme.text;
                }
            }

            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.ticks) {
                        scale.ticks.color = theme.text;
                    }
                    if (scale.grid) {
                        scale.grid.color = theme.grid;
                    }
                    if (scale.title) {
                        scale.title.color = theme.text;
                    }
                });
            }

            chart.update('none');
        });
    }

    // Destroy chart
    destroy(chartId) {
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }
    }

    // Destroy all charts
    destroyAll() {
        Object.keys(this.charts).forEach(chartId => {
            this.destroy(chartId);
        });
    }
}

// Global instance
const finsightCharts = new FinSightCharts();
window.finsightCharts = finsightCharts;

// Theme change observer
const chartThemeObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.attributeName === 'data-bs-theme') {
            setTimeout(() => finsightCharts.updateTheme(), 100);
        }
    });

    // Alert Status Bar Chart
    createAlertStatusChart(canvasId, statusData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const theme = this.getCurrentTheme();

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: statusData.map(item => item.status),
                datasets: [{
                    label: 'Count',
                    data: statusData.map(item => item.count),
                    backgroundColor: statusData.map((item, index) => {
                        const colors = [theme.primary, theme.warning, theme.secondary, theme.danger];
                        return colors[index % colors.length] + '80';
                    }),
                    borderColor: statusData.map((item, index) => {
                        const colors = [theme.primary, theme.warning, theme.secondary, theme.danger];
                        return colors[index % colors.length];
                    }),
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: theme.background,
                        titleColor: theme.text,
                        bodyColor: theme.text,
                        borderColor: theme.grid,
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const item = statusData[context.dataIndex];
                                return `${item.status}: ${item.count} (${item.percentage}%)`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: theme.grid
                        },
                        ticks: {
                            color: theme.text
                        }
                    },
                    x: {
                        grid: {
                            color: theme.grid
                        },
                        ticks: {
                            color: theme.text
                        }
                    }
                }
            }
        });

        this.charts[canvasId] = chart;
        return chart;
    }
});

document.addEventListener('DOMContentLoaded', function() {
    chartThemeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-bs-theme']
    });
});