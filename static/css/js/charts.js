// Initialize Chart.js with default settings
Chart.defaults.font.family = "'Inter', 'system-ui', '-apple-system', 'sans-serif'";
Chart.defaults.color = '#4B5563';
Chart.defaults.plugins.tooltip.backgroundColor = '#1F2937';
Chart.defaults.plugins.legend.labels.usePointStyle = true;

// Custom chart themes
const chartThemes = {
    primary: {
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        borderColor: 'rgb(79, 70, 229)',
        pointBackgroundColor: 'rgb(79, 70, 229)',
    },
    success: {
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderColor: 'rgb(16, 185, 129)',
        pointBackgroundColor: 'rgb(16, 185, 129)',
    },
    warning: {
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        borderColor: 'rgb(245, 158, 11)',
        pointBackgroundColor: 'rgb(245, 158, 11)',
    }
};

// Chart animation configurations
const animations = {
    linear: {
        duration: 1000,
        easing: 'linear'
    },
    easeInOut: {
        duration: 1000,
        easing: 'easeInOutQuart'
    },
    bounce: {
        duration: 1000,
        easing: 'easeInOutBounce'
    }
};

// Create line chart
function createLineChart(ctx, data, options = {}) {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: data.label || 'Values',
                data: data.values,
                fill: true,
                tension: 0.4,
                ...chartThemes.primary,
                ...data.theme
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: animations.easeInOut,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            ...options
        }
    });
}

// Create bar chart
function createBarChart(ctx, data, options = {}) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: data.label || 'Values',
                data: data.values,
                backgroundColor: data.theme && data.theme.backgroundColor || chartThemes.primary.backgroundColor,
                borderColor: data.theme && data.theme.borderColor || chartThemes.primary.borderColor,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: animations.bounce,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            ...options
        }
    });
}

// Create doughnut chart
function createDoughnutChart(ctx, data, options = {}) {
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: data.colors || [
                    'rgb(79, 70, 229)',
                    'rgb(16, 185, 129)',
                    'rgb(245, 158, 11)',
                    'rgb(239, 68, 68)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: animations.easeInOut,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            },
            ...options
        }
    });
}

// Create radar chart
function createRadarChart(ctx, data, options = {}) {
    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: data.labels,
            datasets: [{
                label: data.label || 'Values',
                data: data.values,
                ...chartThemes.primary,
                ...data.theme
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: animations.linear,
            elements: {
                line: {
                    borderWidth: 2
                }
            },
            ...options
        }
    });
}

// Create live updating chart
function createLiveChart(ctx, initialData, updateInterval = 1000) {
    const chart = createLineChart(ctx, initialData);

    setInterval(() => {
        const newValue = Math.random() * 100;
        chart.data.labels.push(new Date().toLocaleTimeString());
        chart.data.datasets[0].data.push(newValue);

        if (chart.data.labels.length > 10) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.update('none');
    }, updateInterval);

    return chart;
}

// Export chart as image
function exportChart(chart, filename = 'chart.png') {
    const link = document.createElement('a');
    link.download = filename;
    link.href = chart.toBase64Image();
    link.click();
}