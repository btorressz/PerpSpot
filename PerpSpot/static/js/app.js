// Crypto Arbitrage Platform JavaScript

class ArbitragePlatform {
    constructor() {
        this.currentToken = 'SOL';
        this.tradingMode = 'spot';
        this.updateInterval = null;
        this.chart = null;
        this.fundingChart = null;
        this.slippageChart = null;
        this.isConnected = false;
        this.refreshRate = 10000; // Default 10 seconds
        
        // Slippage control properties
        this.slippageTolerance = 100; // Default 100 bps
        this.slippageAlertsEnabled = true;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.initChart();
        this.startDataUpdates();
        this.updateConnectionStatus(true);
    }
    
    setupEventListeners() {
        // Token selection
        document.getElementById('token-select').addEventListener('change', (e) => {
            this.currentToken = e.target.value;
            this.updateSelectedToken();
            this.updatePriceData();
        });
        
        // Trading mode selection
        document.querySelectorAll('input[name="trading-mode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.tradingMode = e.target.value;
                this.updateTradingMode();
            });
        });
        
        // Analyze button
        document.getElementById('analyze-btn').addEventListener('click', () => {
            this.analyzeOpportunity();
        });
        
        // Min spread filter
        document.getElementById('min-spread-filter').addEventListener('input', (e) => {
            this.updateOpportunitiesTable();
        });
        
        // Notional amount change
        document.getElementById('notional-amount').addEventListener('input', () => {
            this.updateProfitSimulation();
        });
        
        // Auto-refresh rate selector
        const refreshSelector = document.getElementById('refreshRate');
        if (refreshSelector) {
            refreshSelector.addEventListener('change', (e) => {
                this.refreshRate = parseInt(e.target.value);
                this.restartDataUpdates();
            });
        }
        
        // Slippage control listeners
        document.getElementById('slippage-tolerance').addEventListener('input', (e) => {
            this.handleSlippageToleranceChange(e);
        });
        document.getElementById('advanced-slippage').addEventListener('change', (e) => {
            this.toggleAdvancedSlippage(e);
        });
        document.getElementById('slippage-alerts').addEventListener('change', (e) => {
            this.toggleSlippageAlerts(e);
        });
    }
    
    initChart() {
        const ctx = document.getElementById('spread-chart').getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Max Spread %',
                    data: [],
                    borderColor: '#00d4aa',
                    backgroundColor: 'rgba(0, 212, 170, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Avg Spread %',
                    data: [],
                    borderColor: '#ff6b35',
                    backgroundColor: 'rgba(255, 107, 53, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 300
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#ffffff',
                            usePointStyle: true,
                            padding: 15
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { 
                            color: '#a0a0a0',
                            maxTicksLimit: 8
                        },
                        grid: { 
                            color: 'rgba(255, 255, 255, 0.1)',
                            display: false
                        }
                    },
                    y: {
                        ticks: { 
                            color: '#a0a0a0',
                            maxTicksLimit: 6
                        },
                        grid: { 
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0,
                        hoverRadius: 4
                    }
                }
            }
        });
    }
    
    startDataUpdates() {
        // Initial load
        this.updateMarketOverview();
        this.updatePriceData();
        this.updateOpportunitiesTable();
        this.updateHistoricalChart();
        
        // Set up periodic updates
        this.startPeriodicUpdates();
    }
    
    async updateMarketOverview() {
        try {
            const response = await fetch('/api/market-overview');
            
            // Check if response is ok and content-type is JSON
            if (!response.ok) {
                console.error('Market overview API returned error:', response.status, response.statusText);
                return;
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                console.error('Market overview API returned non-JSON response:', contentType);
                const text = await response.text();
                console.error('Response text:', text.substring(0, 200) + '...');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                const overview = data.data;
                
                document.getElementById('total-opportunities').textContent = overview.total_opportunities || 0;
                document.getElementById('max-spread').textContent = 
                    overview.max_spread_pct ? `${overview.max_spread_pct.toFixed(2)}%` : '--%';
                document.getElementById('avg-spread').textContent = 
                    overview.avg_spread_pct ? `${overview.avg_spread_pct.toFixed(2)}%` : '--%';
                document.getElementById('tokens-tracked').textContent = overview.supported_tokens || 0;
            }
        } catch (error) {
            console.error('Error updating market overview:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    async updatePriceData() {
        try {
            const response = await fetch(`/api/prices?token=${this.currentToken}`);
            const data = await response.json();
            
            if (data.success && data.data) {
                const tokenData = data.data;
                
                // Update Jupiter price
                const jupiterData = tokenData.jupiter || {};
                const jupiterPrice = jupiterData.spot_price || jupiterData.price || 0;
                document.getElementById('jupiter-price').textContent = 
                    jupiterPrice > 0 ? `$${jupiterPrice.toFixed(4)}` : '$--';
                
                // Update Hyperliquid price
                const hyperliquidData = tokenData.hyperliquid || {};
                const hyperliquidPrice = hyperliquidData.mark_price || 0;
                document.getElementById('hyperliquid-price').textContent = 
                    hyperliquidPrice > 0 ? `$${hyperliquidPrice.toFixed(4)}` : '$--';
                
                // Update funding rate
                const fundingRate = hyperliquidData.funding_rate || 0;
                document.getElementById('hyperliquid-funding').textContent = 
                    `Funding: ${(fundingRate * 100).toFixed(3)}%`;
                
                // Calculate and update spread
                if (jupiterPrice > 0 && hyperliquidPrice > 0) {
                    const spreadPct = ((hyperliquidPrice - jupiterPrice) / jupiterPrice) * 100;
                    document.getElementById('spread-value').textContent = `${spreadPct.toFixed(2)}%`;
                    
                    const spreadElement = document.getElementById('spread-value');
                    const directionElement = document.getElementById('spread-direction');
                    
                    if (spreadPct > 0.5) {
                        spreadElement.className = 'price-value spread-positive';
                        directionElement.textContent = 'Perp Premium';
                        directionElement.className = 'price-change spread-positive';
                    } else if (spreadPct < -0.5) {
                        spreadElement.className = 'price-value spread-negative';
                        directionElement.textContent = 'Spot Premium';
                        directionElement.className = 'price-change spread-negative';
                    } else {
                        spreadElement.className = 'price-value spread-neutral';
                        directionElement.textContent = 'Fair Value';
                        directionElement.className = 'price-change spread-neutral';
                    }
                }
                
                this.updateConnectionStatus(true);
            }
        } catch (error) {
            console.error('Error updating price data:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    async updateOpportunitiesTable() {
        try {
            const minSpread = document.getElementById('min-spread-filter').value;
            const response = await fetch(`/api/arbitrage?min_spread=${minSpread}`);
            const data = await response.json();
            
            if (data.success) {
                const opportunities = data.data;
                const tbody = document.getElementById('opportunities-table');
                
                if (opportunities.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="8" class="text-center text-muted">
                                <i class="fas fa-search me-2"></i>No arbitrage opportunities found above ${minSpread}% spread
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                tbody.innerHTML = opportunities.map(opp => {
                    const liquidityScore = opp.liquidity_score || 0;
                    const liquidityWidth = Math.max(liquidityScore * 100, 5);
                    
                    // Extract slippage information if available
                    const slippageBps = opp.slippage_estimate_bps || 0;
                    // Color code: Green <= 50 bps, Orange 50-200 bps, Red > 200 bps
                    const slippageClass = slippageBps > 200 ? 'text-danger' : slippageBps > 50 ? 'text-warning' : 'text-success';
                    
                    return `
                        <tr>
                            <td>
                                <strong>${opp.token}</strong>
                            </td>
                            <td>$${opp.spot_price.toFixed(4)}</td>
                            <td>$${opp.perp_price.toFixed(4)}</td>
                            <td>
                                <span class="${opp.spread_pct > 0 ? 'spread-positive' : 'spread-negative'}">
                                    ${opp.spread_pct > 0 ? '+' : ''}${opp.spread_pct.toFixed(2)}%
                                </span>
                                <br>
                                <small class="${slippageClass}">
                                    <i class="fas fa-tachometer-alt me-1"></i>${slippageBps.toFixed(1)} bps slippage
                                </small>
                            </td>
                            <td>
                                <span class="strategy-badge ${opp.strategy === 'long_spot_short_perp' ? 'strategy-long-short' : 'strategy-short-long'}">
                                    ${opp.direction}
                                </span>
                            </td>
                            <td>
                                <span class="text-success">
                                    $${(opp.potential_profit?.net_profit || 0).toFixed(2)}
                                </span>
                                <br>
                                <small class="text-muted">
                                    ${(opp.potential_profit?.roi_pct || 0).toFixed(1)}% ROI
                                </small>
                            </td>
                            <td>
                                <div class="liquidity-score">
                                    <div class="liquidity-fill" style="width: ${liquidityWidth}%"></div>
                                </div>
                                <br>
                                <small class="text-muted">${(liquidityScore * 100).toFixed(0)}%</small>
                            </td>
                            <td>
                                <button class="btn btn-sm btn-success" onclick="app.analyzeToken('${opp.token}')">
                                    <i class="fas fa-chart-line me-1"></i>Analyze
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }
        } catch (error) {
            console.error('Error updating opportunities table:', error);
        }
    }
    
    async updateHistoricalChart() {
        try {
            const response = await fetch('/api/historical?hours=24');
            const data = await response.json();
            
            if (data.success && data.data.length > 0) {
                const historicalData = data.data;
                
                const labels = historicalData.map(point => {
                    const date = new Date(point.timestamp);
                    return date.toLocaleTimeString('en-US', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    });
                });
                
                const maxSpreads = historicalData.map(point => point.max_spread);
                const avgSpreads = historicalData.map(point => point.avg_spread);
                
                // Keep only last 15 points for better performance
                if (labels.length > 15) {
                    labels.splice(0, labels.length - 15);
                    maxSpreads.splice(0, maxSpreads.length - 15);
                    avgSpreads.splice(0, avgSpreads.length - 15);
                }
                
                this.chart.data.labels = labels;
                this.chart.data.datasets[0].data = maxSpreads;
                this.chart.data.datasets[1].data = avgSpreads;
                this.chart.update('none');
            }
        } catch (error) {
            console.error('Error updating historical chart:', error);
        }
    }
    
    async analyzeOpportunity() {
        const analyzeBtn = document.getElementById('analyze-btn');
        const originalText = analyzeBtn.innerHTML;
        
        try {
            analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...';
            analyzeBtn.disabled = true;
            
            const size = document.getElementById('notional-amount').value || 1000;
            const response = await fetch(`/api/bridge-arb?token=${this.currentToken}&size=${size}&latency=fast`);
            const data = await response.json();
            
            if (data.success) {
                const analysisData = data.data;
                
                // Update profit display with actual data structure
                this.updateProfitDisplay({
                    gross_profit: analysisData.profit.gross_profit,
                    total_fees: analysisData.costs.total_fees,
                    net_profit: analysisData.profit.net_profit,
                    roi_pct: analysisData.profit.roi_pct
                });
                
                // Show analysis results
                this.showAnalysisResults(analysisData);
            } else {
                this.showError(data.error || `Failed to analyze ${this.currentToken}`);
            }
        } catch (error) {
            console.error('Error analyzing opportunity:', error);
            this.showError('Failed to analyze opportunity');
        } finally {
            analyzeBtn.innerHTML = originalText;
            analyzeBtn.disabled = false;
        }
    }
    
    updateProfitDisplay(profitData) {
        if (!profitData) return;
        
        document.getElementById('gross-profit').textContent = `$${profitData.gross_profit.toFixed(2)}`;
        document.getElementById('total-fees').textContent = `$${profitData.total_fees.toFixed(2)}`;
        document.getElementById('net-profit').textContent = `$${profitData.net_profit.toFixed(2)}`;
        document.getElementById('roi-pct').textContent = `${profitData.roi_pct.toFixed(2)}%`;
    }
    
    async updateProfitSimulation() {
        // Update profit simulation based on current notional amount and selected token
        try {
            const size = document.getElementById('notional-amount').value || 1000;
            const response = await fetch(`/api/bridge-arb?token=${this.currentToken}&size=${size}&latency=fast`);
            const data = await response.json();
            
            if (data.success && data.data.profit) {
                this.updateProfitDisplay({
                    gross_profit: data.data.profit.gross_profit,
                    total_fees: data.data.costs.total_fees,
                    net_profit: data.data.profit.net_profit,
                    roi_pct: data.data.profit.roi_pct
                });
            }
        } catch (error) {
            console.log('Error updating profit simulation:', error);
            // Silent error - not critical for UI operation
        }
    }
    
    updateSelectedToken() {
        document.getElementById('selected-token').textContent = this.currentToken;
    }
    
    updateTradingMode() {
        // Update UI based on selected trading mode
        const modeLabels = document.querySelectorAll('.btn-check + label');
        modeLabels.forEach(label => {
            label.classList.remove('active');
        });
        
        document.querySelector(`#mode-${this.tradingMode} + label`).classList.add('active');
    }
    
    updateLastUpdateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { 
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        document.getElementById('last-update').textContent = timeString;
    }
    
    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connection-status');
        const iconElement = statusElement.previousElementSibling;
        
        if (connected) {
            statusElement.textContent = 'Connected';
            iconElement.className = 'fas fa-circle text-success me-1';
        } else {
            statusElement.textContent = 'Disconnected';
            iconElement.className = 'fas fa-circle text-danger me-1';
        }
    }
    
    analyzeToken(token) {
        // Set the token and update
        document.getElementById('token-select').value = token;
        this.currentToken = token;
        this.updateSelectedToken();
        this.updatePriceData();
        this.analyzeOpportunity();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    showAnalysisResults(data) {
        // You could implement a modal or notification here
        console.log('Analysis results:', data);
        
        // Update strategy text based on analysis
        const spread = data.prices.spread_pct;
        const strategyElement = document.getElementById('strategy-text');
        
        if (Math.abs(spread) < 0.5) {
            strategyElement.textContent = 'Monitor - Low spread';
        } else if (data.profit.net_profit > 10) {
            strategyElement.textContent = spread > 0 ? 'Long Jupiter, Short Hyperliquid' : 'Long Hyperliquid, Short Jupiter';
        } else {
            strategyElement.textContent = 'Monitor - High fees relative to spread';
        }
    }
    
    showError(message) {
        // Simple error display - you could implement toast notifications
        console.error(message);
        
        // You could show a toast notification here
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger position-fixed top-0 end-0 m-3';
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        document.body.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentElement) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ArbitragePlatform();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.destroy();
    }
});

// Utility functions
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    
    if (Math.abs(num) >= 1e9) {
        return (num / 1e9).toFixed(decimals) + 'B';
    } else if (Math.abs(num) >= 1e6) {
        return (num / 1e6).toFixed(decimals) + 'M';
    } else if (Math.abs(num) >= 1e3) {
        return (num / 1e3).toFixed(decimals) + 'K';
    } else {
        return num.toFixed(decimals);
    }
}

function formatPercentage(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '--%';
    return `${num.toFixed(decimals)}%`;
}

function formatCurrency(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '$--';
    return `$${formatNumber(num, decimals)}`;
}

// Live price dashboard function
function updateLivePrices() {
    fetch('/api/prices')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data) {
                const livePricesGrid = document.getElementById('live-prices-grid');
                if (!livePricesGrid) return;
                
                const tokens = ['SOL', 'ETH', 'JUP', 'BONK', 'ORCA', 'HL', 'USDC', 'USDT'];
                const tokenNames = {
                    'SOL': 'Solana',
                    'ETH': 'Ethereum', 
                    'JUP': 'Jupiter',
                    'BONK': 'Bonk',
                    'ORCA': 'Orca',
                    'HL': 'Hyperliquid',
                    'USDC': 'USD Coin',
                    'USDT': 'Tether'
                };
                
                livePricesGrid.innerHTML = tokens.map(token => {
                    const tokenData = data.data[token] || {};
                    const jupiterData = tokenData.jupiter || {};
                    const hyperliquidData = tokenData.hyperliquid || {};
                    
                    const spotPrice = jupiterData.spot_price || jupiterData.price || 0;
                    const perpPrice = hyperliquidData.mark_price || 0;
                    const fundingRate = hyperliquidData.funding_rate || 0;
                    
                    let spread = 0;
                    let spreadClass = '';
                    let spreadDirection = 'No Data';
                    
                    if (spotPrice > 0 && perpPrice > 0) {
                        spread = ((perpPrice - spotPrice) / spotPrice) * 100;
                        if (spread > 0.1) {
                            spreadClass = 'positive-spread';
                            spreadDirection = '+' + spread.toFixed(2) + '%';
                        } else if (spread < -0.1) {
                            spreadClass = 'negative-spread';
                            spreadDirection = spread.toFixed(2) + '%';
                        } else {
                            spreadDirection = spread.toFixed(2) + '%';
                        }
                    }
                    
                    const badgeClass = spread > 0.1 ? 'bg-success' : spread < -0.1 ? 'bg-danger' : 'bg-secondary';
                    
                    return `
                        <div class="col-md-6 col-lg-4 col-xl-3">
                            <div class="live-price-card ${spreadClass}">
                                <div class="token-header">
                                    <div>
                                        <div class="token-symbol">${token}</div>
                                        <div class="token-name">${tokenNames[token]}</div>
                                    </div>
                                    <span class="badge ${badgeClass} spread-badge">${spreadDirection}</span>
                                </div>
                                <div class="price-row">
                                    <span class="price-label">
                                        <i class="fas fa-rocket me-1"></i>Spot
                                    </span>
                                    <span class="price-value jupiter-price">
                                        ${spotPrice > 0 ? '$' + spotPrice.toFixed(4) : 'N/A'}
                                    </span>
                                </div>
                                <div class="price-row">
                                    <span class="price-label">
                                        <i class="fas fa-fire me-1"></i>Perp
                                    </span>
                                    <span class="price-value hyperliquid-price">
                                        ${perpPrice > 0 ? '$' + perpPrice.toFixed(4) : 'N/A'}
                                    </span>
                                </div>
                                <div class="funding-rate">
                                    <i class="fas fa-percentage me-1"></i>
                                    Funding: ${(fundingRate * 100).toFixed(3)}%/hr
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        })
        .catch(error => console.error('Error updating live prices:', error));
}

// Add to update cycle
document.addEventListener('DOMContentLoaded', function() {
    updateLivePrices();
    setInterval(updateLivePrices, 2000); // 2-second updates with Redis caching
});

// Auto-refresh functionality extensions
ArbitragePlatform.prototype.startPeriodicUpdates = function() {
    // Clear existing interval
    if (this.updateInterval) {
        clearInterval(this.updateInterval);
    }
    
    // Only start if refresh rate is not manual (0)
    if (this.refreshRate > 0) {
        this.updateInterval = setInterval(() => {
            this.updateMarketOverview();
            this.updatePriceData();
            this.updateOpportunitiesTable();
            this.updateHistoricalChart();
            this.updateFundingChart();
            this.updateLastUpdateTime();
        }, this.refreshRate);
    }
};

ArbitragePlatform.prototype.restartDataUpdates = function() {
    this.startPeriodicUpdates();
    // Immediately update when changing refresh rate
    if (this.refreshRate > 0) {
        this.updateMarketOverview();
        this.updatePriceData();
        this.updateOpportunitiesTable();
        this.updateHistoricalChart();
        this.updateFundingChart();
    }
};

ArbitragePlatform.prototype.updateFundingChart = async function() {
    try {
        const response = await fetch(`/api/funding/history?token=${this.currentToken}&hours=24`);
        const data = await response.json();
        
        if (data.success && data.data) {
            const fundingData = data.data.funding_rates;
            
            // Initialize funding chart if it doesn't exist
            if (!this.fundingChart) {
                this.initFundingChart();
            }
            
            // Update chart data
            const labels = fundingData.map(item => {
                const date = new Date(item.timestamp);
                return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            });
            
            const currentRates = fundingData.map(item => item.funding_rate_bps);
            const rollingAvg = fundingData.map(item => item.funding_rate_24h_avg * 10000); // Convert to bps
            
            this.fundingChart.data.labels = labels;
            this.fundingChart.data.datasets[0].data = currentRates;
            this.fundingChart.data.datasets[1].data = rollingAvg;
            this.fundingChart.update('none'); // No animation for real-time updates
        }
    } catch (error) {
        console.error('Error updating funding chart:', error);
    }
};

ArbitragePlatform.prototype.initFundingChart = function() {
    const ctx = document.getElementById('funding-chart');
    if (!ctx) return; // Chart container not found
    
    this.fundingChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Current Funding Rate (bps)',
                data: [],
                borderColor: '#ff6b35',
                backgroundColor: 'rgba(255, 107, 53, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            }, {
                label: '24h Rolling Average (bps)',
                data: [],
                borderColor: '#00d4aa',
                backgroundColor: 'rgba(0, 212, 170, 0.1)',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff'
                    }
                },
                title: {
                    display: true,
                    text: 'Funding Rate Trends',
                    color: '#ffffff'
                }
            },
            scales: {
                x: {
                    ticks: { color: '#a0a0a0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: { 
                        color: '#a0a0a0',
                        callback: function(value) {
                            return value.toFixed(2) + ' bps';
                        }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            },
            elements: {
                point: {
                    radius: 0,
                    hoverRadius: 6
                }
            }
        }
    });
};

// Initialize slippage visualization chart
ArbitragePlatform.prototype.initSlippageChart = function() {
    const ctx = document.getElementById('slippage-chart');
    if (!ctx) return;
    
    this.slippageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['$100', '$500', '$1K', '$5K', '$10K', '$25K', '$50K'],
            datasets: [{
                label: 'Jupiter Slippage',
                data: [8, 15, 28, 65, 120, 250, 450],
                borderColor: '#ff9500',
                backgroundColor: 'rgba(255, 149, 0, 0.1)',
                fill: true,
                tension: 0.4
            }, {
                label: 'Hyperliquid Slippage',
                data: [2, 4, 8, 18, 35, 75, 140],
                borderColor: '#00d4aa',
                backgroundColor: 'rgba(0, 212, 170, 0.1)',
                fill: true,
                tension: 0.4
            }, {
                label: 'Your Tolerance',
                data: [100, 100, 100, 100, 100, 100, 100],
                borderColor: '#ffc107',
                backgroundColor: 'transparent',
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff',
                        usePointStyle: true
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#a0a0a0' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    title: {
                        display: true,
                        text: 'Trade Size',
                        color: '#ffffff'
                    }
                },
                y: {
                    ticks: { 
                        color: '#a0a0a0',
                        callback: function(value) { return value + ' bps'; }
                    },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    title: {
                        display: true,
                        text: 'Slippage (bps)',
                        color: '#ffffff'
                    }
                }
            },
            elements: {
                point: {
                    radius: 4,
                    hoverRadius: 6
                }
            }
        }
    });
};

// Slippage Control Methods
ArbitragePlatform.prototype.handleSlippageToleranceChange = function(e) {
        const tolerance = parseFloat(e.target.value);
        document.getElementById('slippage-value').textContent = tolerance;
        
        // Update slippage preferences
        this.slippageTolerance = tolerance;
        
        // Update the expected slippage display
        this.updateExpectedSlippage();
        
        // Check if current opportunities exceed tolerance
        this.checkSlippageWarnings();
};
    
ArbitragePlatform.prototype.toggleAdvancedSlippage = function(e) {
        const advancedControls = document.getElementById('advanced-slippage-controls');
        if (e.target.checked) {
            advancedControls.style.display = 'block';
        } else {
            advancedControls.style.display = 'none';
        }
};
    
ArbitragePlatform.prototype.toggleSlippageAlerts = function(e) {
        this.slippageAlertsEnabled = e.target.checked;
        if (!this.slippageAlertsEnabled) {
            // Hide any current alerts
            const alertElement = document.getElementById('slippage-alert');
            alertElement.classList.add('d-none');
        }
};
    
ArbitragePlatform.prototype.updateExpectedSlippage = async function() {
        try {
            const notional = document.getElementById('notional-amount').value || 1000;
            const token = this.currentToken;
            
            // Get estimated slippage from backend
            const response = await fetch(`/api/slippage-estimate?token=${token}&size=${notional}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    const expectedBps = data.slippage_bps;
                    document.getElementById('expected-slippage').textContent = expectedBps.toFixed(1) + ' bps';
                    
                    // Update progress bar
                    const percentage = Math.min((expectedBps / 250) * 100, 100); // Scale to 250 bps max for visualization
                    const progressBar = document.getElementById('slippage-bar');
                    progressBar.style.width = percentage + '%';
                    
                    // Color code based on specific bps thresholds
                    // Green: <= 50 bps (Low slippage)
                    // Orange: 50-200 bps (Medium slippage)  
                    // Red: > 200 bps (High slippage)
                    if (expectedBps > 200) {
                        progressBar.className = 'progress-bar bg-danger';
                    } else if (expectedBps > 50) {
                        progressBar.className = 'progress-bar bg-warning';
                    } else {
                        progressBar.className = 'progress-bar bg-success';
                    }
                    
                    // Also update tolerance-based indicator if it exists
                    const toleranceIndicator = document.getElementById('tolerance-indicator');
                    if (toleranceIndicator) {
                        if (expectedBps > this.slippageTolerance) {
                            toleranceIndicator.className = 'tolerance-indicator bg-danger';
                            toleranceIndicator.textContent = 'Above Tolerance';
                        } else if (expectedBps > this.slippageTolerance * 0.8) {
                            toleranceIndicator.className = 'tolerance-indicator bg-warning';
                            toleranceIndicator.textContent = 'Near Tolerance';
                        } else {
                            toleranceIndicator.className = 'tolerance-indicator bg-success';
                            toleranceIndicator.textContent = 'Within Tolerance';
                        }
                    }
                }
            }
        } catch (error) {
            console.log('Could not update expected slippage:', error);
            document.getElementById('expected-slippage').textContent = '--';
        }
};
    
ArbitragePlatform.prototype.checkSlippageWarnings = function() {
        if (!this.slippageAlertsEnabled) return;
        
        const alertElement = document.getElementById('slippage-alert');
        const alertText = document.getElementById('slippage-alert-text');
        
        // Check opportunities table for high slippage
        const opportunities = document.querySelectorAll('#opportunities-table tr');
        let highSlippageOpps = 0;
        
        opportunities.forEach(row => {
            const slippageCell = row.querySelector('.text-danger, .text-warning');
            if (slippageCell && slippageCell.textContent.includes('bps')) {
                const slippageBps = parseFloat(slippageCell.textContent.match(/[\d.]+/)[0]);
                if (slippageBps > this.slippageTolerance) {
                    highSlippageOpps++;
                }
            }
        });
        
        if (highSlippageOpps > 0) {
            alertText.textContent = `${highSlippageOpps} opportunity${highSlippageOpps > 1 ? 'ies' : 'y'} exceed${highSlippageOpps > 1 ? '' : 's'} your ${this.slippageTolerance} bps tolerance`;
            alertElement.classList.remove('d-none');
        } else {
            alertElement.classList.add('d-none');
        }
};

// Export for external use
window.ArbitragePlatform = ArbitragePlatform;
