/**
 * Dashboard JavaScript functionality
 * Handles chart initialization and data visualization
 */

let salesChart = null;

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
    const brandColor = brand === 'URBRAND' ? '#0d6efd' : '#198754';
    
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
                pointRadius: 5,
                pointHoverRadius: 7,
                pointHoverBackgroundColor: brandColor,
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            weight: '500'
                        },
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: brandColor,
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `Sales: ${formatCurrency(context.parsed.y)} EGP`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            weight: '500'
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        font: {
                            weight: '500'
                        },
                        callback: function(value) {
                            return formatCurrency(value) + ' EGP';
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            animation: {
                duration: 2000,
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
