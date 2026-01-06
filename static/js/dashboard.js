/**
 * Dashboard JavaScript functionality
 * Handles chart initialization and data visualization
 */

let salesChart = null;
let topProductsChart = null;

// Modern color palette for charts
const chartColors = {
    primary: '#A25D28',
    secondary: '#D9A05B',
    success: '#10B981',
    warning: '#F59E0B',
    danger: '#EF4444',
    info: '#3B82F6',
    gradients: [
        '#A25D28', '#D9A05B', '#10B981', '#3B82F6', '#F59E0B',
        '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16', '#F97316'
    ]
};

/**
 * Initialize the sales chart for the specified brand
 * @param {string} brand - The brand name (URBRAND or SURVACCI)
 */
function initSalesChart(brand) {
    const ctx = document.getElementById('salesChart');
    if (!ctx) {
        console.error('Sales chart canvas not found');
        return;
    }

    // Destroy existing chart if it exists
    if (salesChart) {
        salesChart.destroy();
    }

    // Show loading state
    ctx.style.opacity = '0.5';

    // Fetch chart data from the API
    fetch(`/api/sales-chart/${brand}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            createSalesChart(ctx, data, brand);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            showChartError(ctx);
        })
        .finally(() => {
            ctx.style.opacity = '1';
        });
}

/**
 * Create the sales chart with the provided data
 * @param {HTMLCanvasElement} ctx - The canvas context
 * @param {Object} data - Chart data with labels and values
 * @param {string} brand - The brand name
 */
function createSalesChart(ctx, data, brand) {
    const brandColor = brand === 'URBRAND' ? chartColors.primary : chartColors.success;
    
    salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: `${brand} Sales (EGP)`,
                data: data.data,
                borderColor: brandColor,
                backgroundColor: brandColor + '20',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: brandColor,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointHoverBackgroundColor: brandColor,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 3
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
                    backgroundColor: 'rgba(47, 47, 47, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: brandColor,
                    borderWidth: 1,
                    cornerRadius: 12,
                    displayColors: false,
                    titleFont: {
                        size: 14,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 13,
                        weight: '500'
                    },
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            return `Revenue: ${formatCurrency(context.parsed.y)} EGP`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        padding: 8
                    }
                },
                y: {
                    beginAtZero: true,
                    border: {
                        display: false
                    },
                    grid: {
                        color: '#E5E7EB',
                        drawTicks: false
                    },
                    ticks: {
                        color: '#6B7280',
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        padding: 8,
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
}

/**
 * Initialize the top products pie chart
 * @param {Array} productsData - Array of [product_name, quantity] tuples
 */
function initTopProductsChart(productsData) {
    const ctx = document.getElementById('topProductsChart');
    if (!ctx || !productsData || productsData.length === 0) {
        return;
    }

    // Destroy existing chart if it exists
    if (topProductsChart) {
        topProductsChart.destroy();
    }

    const labels = productsData.map(item => item[0]);
    const data = productsData.map(item => item[1]);
    const colors = chartColors.gradients.slice(0, labels.length);

    topProductsChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 3,
                hoverBorderWidth: 4,
                hoverOffset: 8
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
                    backgroundColor: 'rgba(47, 47, 47, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderWidth: 0,
                    cornerRadius: 12,
                    titleFont: {
                        size: 14,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 13,
                        weight: '500'
                    },
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            const total = data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.parsed / total) * 100);
                            return `${context.label}: ${context.parsed} pieces (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%',
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            }
        }
    });
}

/**
 * Show error message when chart fails to load
 * @param {HTMLCanvasElement} ctx - The canvas context
 */
function showChartError(ctx) {
    const container = ctx.parentElement;
    container.innerHTML = `
        <div class="text-center text-muted py-5">
            <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
            <h5>Unable to load chart</h5>
            <p>There was an error loading the sales data. Please try refreshing the page.</p>
            <button class="btn btn-outline-primary" onclick="window.location.reload()">
                <i class="fas fa-refresh"></i> Refresh Page
            </button>
        </div>
    `;
}

/**
 * Format currency numbers with thousand separators
 * @param {number} amount - The amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Refresh chart data for the current brand
 */
function refreshChart() {
    const brandButtons = document.querySelectorAll('.btn-group .btn-primary');
    let currentBrand = 'URBRAND';
    
    brandButtons.forEach(button => {
        if (button.textContent.trim() === 'SURVACCI') {
            currentBrand = 'SURVACCI';
        }
    });
    
    initSalesChart(currentBrand);
}

// Auto-refresh chart data every 5 minutes
setInterval(refreshChart, 5 * 60 * 1000);

// Handle responsive chart resizing
window.addEventListener('resize', function() {
    if (salesChart) {
        salesChart.resize();
    }
});

// Initialize chart when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Chart will be initialized by the template script
    console.log('Dashboard JavaScript loaded successfully');
});
