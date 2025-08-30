/**
 * Bridge Analytics Extension
 * Enhanced analytics functionality for the bridge arbitrage system
 */

// Extend the BridgeArbitrageUI class with analytics methods
BridgeArbitrageUI.prototype.loadBridgeAnalytics = async function(selectedToken = null) {
    try {
        const btn = document.getElementById('bridgeAnalyticsBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        
        // Get token from bridge selection or fallback to current selection
        const token = selectedToken || document.getElementById('bridgeToken')?.value || 'SOL';
        
        const response = await fetch(`/api/bridge/analytics?hours=24&token=${token}`);
        const data = await response.json();
        
        if (data.success) {
            this.displayBridgeAnalytics(data.data, token);
            document.getElementById('bridgeAnalytics').style.display = 'block';
            
            // Scroll to analytics section
            document.getElementById('bridgeAnalytics').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        } else {
            this.showAlert(`Failed to load analytics for ${token}: ` + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Failed to load bridge analytics:', error);
        this.showAlert('Failed to load analytics', 'danger');
    } finally {
        const btn = document.getElementById('bridgeAnalyticsBtn');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-chart-line"></i> Analytics';
    }
};

BridgeArbitrageUI.prototype.displayBridgeAnalytics = function(analytics, token = 'SOL') {
    // Create comprehensive analytics HTML
    const analyticsHtml = `
        <div class="analytics-dashboard">
            <div class="row mb-4">
                <div class="col-12">
                    <h5 class="text-center mb-4">
                        <i class="fas fa-chart-bar me-2"></i>
                        ${token} Bridge Arbitrage Analytics (Last 24 Hours)
                    </h5>
                    <div class="text-center mb-3">
                        <span class="badge bg-primary">${token}-USDC Trading Pair</span>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="analytics-card">
                        <div class="analytics-icon">
                            <i class="fas fa-calculator"></i>
                        </div>
                        <div class="analytics-value">${analytics.total_simulations || 0}</div>
                        <div class="analytics-label">Total Simulations</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="analytics-card">
                        <div class="analytics-icon">
                            <i class="fas fa-check-circle text-success"></i>
                        </div>
                        <div class="analytics-value">${analytics.viable_opportunities || 0}</div>
                        <div class="analytics-label">Viable Opportunities</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="analytics-card">
                        <div class="analytics-icon">
                            <i class="fas fa-percentage"></i>
                        </div>
                        <div class="analytics-value">${analytics.analytics?.profitability_metrics?.success_rate?.toFixed(1) || '0.0'}%</div>
                        <div class="analytics-label">Success Rate</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="analytics-card">
                        <div class="analytics-icon">
                            <i class="fas fa-dollar-sign text-warning"></i>
                        </div>
                        <div class="analytics-value">$${analytics.analytics?.profitability_metrics?.total_potential_profit?.toFixed(2) || '0.00'}</div>
                        <div class="analytics-label">Total Profit Potential</div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="analytics-section">
                        <h6><i class="fas fa-chart-pie me-2"></i>Volume Analysis</h6>
                        <div class="volume-metrics">
                            <div class="metric">
                                <span class="label">Total Volume:</span>
                                <span class="value">$${analytics.analytics?.volume_analytics?.total_volume?.toLocaleString() || '0'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Viable Volume:</span>
                                <span class="value">$${analytics.analytics?.volume_analytics?.viable_volume?.toLocaleString() || '0'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Avg Trade Size:</span>
                                <span class="value">$${analytics.analytics?.volume_analytics?.avg_trade_size?.toLocaleString() || '0'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="analytics-section">
                        <h6><i class="fas fa-clock me-2"></i>Latency Analysis</h6>
                        <div class="latency-metrics">
                            <div class="metric">
                                <span class="label">Avg Execution Time:</span>
                                <span class="value">${analytics.analytics?.latency_analysis?.avg_execution_time?.toFixed(2) || '0.00'}s</span>
                            </div>
                            <div class="metric">
                                <span class="label">95th Percentile:</span>
                                <span class="value">${analytics.analytics?.latency_analysis?.p95_execution_time?.toFixed(2) || '0.00'}s</span>
                            </div>
                            <div class="metric">
                                <span class="label">Fastest:</span>
                                <span class="value">${analytics.analytics?.latency_analysis?.fastest_execution?.toFixed(2) || '0.00'}s</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="analytics-section">
                        <h6><i class="fas fa-coins me-2"></i>Token Performance</h6>
                        <div class="token-performance">
                            ${Object.entries(analytics.analytics?.volume_analytics?.volume_by_token || {}).map(([token, volume]) => `
                                <div class="token-stat">
                                    <div class="token-info">
                                        <span class="token-name">${token}</span>
                                        <span class="token-badge">
                                            <i class="fas fa-chart-line"></i>
                                        </span>
                                    </div>
                                    <div class="token-metrics">
                                        <div class="metric-item">
                                            <span class="metric-label">Volume</span>
                                            <span class="metric-value">$${volume.toLocaleString()}</span>
                                        </div>
                                        <div class="metric-item">
                                            <span class="metric-label">Profit</span>
                                            <span class="metric-value">$${(analytics.analytics?.profitability_metrics?.profit_by_token?.[token] || 0).toFixed(2)}</span>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="analytics-section">
                        <h6><i class="fas fa-chart-area me-2"></i>Spread Analysis</h6>
                        <div class="spread-metrics">
                            <div class="metric">
                                <span class="label">Avg Spread:</span>
                                <span class="value">${analytics.analytics?.spread_analysis?.avg_spread_bps?.toFixed(1) || '0.0'} bps</span>
                            </div>
                            <div class="metric">
                                <span class="label">Max Spread:</span>
                                <span class="value">${analytics.analytics?.spread_analysis?.max_spread_bps?.toFixed(1) || '0.0'} bps</span>
                            </div>
                            <div class="metric">
                                <span class="label">Min Viable Spread:</span>
                                <span class="value">${analytics.analytics?.spread_analysis?.viable_spread_threshold?.toFixed(1) || '0.0'} bps</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            ${analytics.total_simulations === 0 ? `
                <div class="row">
                    <div class="col-12">
                        <div class="no-data-message">
                            <i class="fas fa-info-circle"></i>
                            <p>No simulation data available yet. Run some bridge simulations to see analytics.</p>
                            <button class="btn btn-primary" onclick="bridgeArbitrageUI.runUnifiedAnalysis()">
                                <i class="fas fa-play"></i> Run Analysis
                            </button>
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    
    // Update analytics container
    const analyticsContainer = document.getElementById('bridgeAnalytics');
    analyticsContainer.innerHTML = analyticsHtml;
};

// Enhanced analytics for advanced simulations
BridgeArbitrageUI.prototype.runAdvancedSimulation = async function() {
    try {
        const btn = document.getElementById('simulateAdvancedBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating...';

        const token = document.getElementById('bridgeToken').value;
        const size = document.getElementById('bridgeSize').value;
        const template = document.getElementById('executionTemplate').value;

        const response = await fetch(`/api/bridge/simulate?token=${token}&size=${size}${template ? '&template=' + encodeURIComponent(template) : ''}`);
        const data = await response.json();

        if (data.success) {
            this.displaySimulationResults(data.data);
            // Automatically load analytics after simulation
            setTimeout(() => {
                this.loadBridgeAnalytics();
            }, 1000);
        } else {
            this.showAlert('Simulation failed: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Advanced simulation error:', error);
        this.showAlert('Failed to run advanced simulation', 'danger');
    } finally {
        const btn = document.getElementById('simulateAdvancedBtn');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-calculator"></i> Simulate Execution';
    }
};

// Enhanced CSS for analytics
const analyticsStyles = `
<style>
.analytics-dashboard {
    background: rgba(255,255,255,0.05);
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-top: 1rem;
}

.analytics-card {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 0.5rem;
    padding: 1.5rem;
    text-align: center;
    margin-bottom: 1rem;
    transition: transform 0.2s ease;
}

.analytics-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.analytics-icon {
    font-size: 2rem;
    margin-bottom: 1rem;
    opacity: 0.8;
}

.analytics-value {
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
    color: #fff;
}

.analytics-label {
    font-size: 0.875rem;
    opacity: 0.8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.analytics-section {
    background: rgba(255,255,255,0.05);
    border-radius: 0.375rem;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid rgba(255,255,255,0.1);
}

.analytics-section h6 {
    margin-bottom: 1rem;
    color: #fff;
    font-weight: 600;
}

.metric {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.metric:last-child {
    border-bottom: none;
}

.metric .label {
    font-weight: 500;
    opacity: 0.9;
}

.metric .value {
    font-weight: bold;
    color: #28a745;
}

.token-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    margin-bottom: 0.5rem;
    background: rgba(255,255,255,0.05);
    border-radius: 0.375rem;
    border: 1px solid rgba(255,255,255,0.1);
}

.token-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.token-name {
    font-weight: bold;
    font-size: 1.1rem;
}

.token-badge {
    background: rgba(40, 167, 69, 0.2);
    color: #28a745;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
}

.token-metrics {
    display: flex;
    gap: 1rem;
}

.metric-item {
    text-align: right;
}

.metric-label {
    display: block;
    font-size: 0.75rem;
    opacity: 0.7;
    margin-bottom: 0.25rem;
}

.metric-value {
    display: block;
    font-weight: bold;
    font-size: 0.9rem;
}

.no-data-message {
    text-align: center;
    padding: 3rem;
    background: rgba(255,255,255,0.05);
    border-radius: 0.5rem;
    border: 2px dashed rgba(255,255,255,0.2);
}

.no-data-message i {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.6;
}

.no-data-message p {
    font-size: 1.1rem;
    margin-bottom: 1.5rem;
    opacity: 0.8;
}
</style>
`;

// Add analytics styles to page
document.addEventListener('DOMContentLoaded', function() {
    if (!document.getElementById('bridge-analytics-styles')) {
        const styleElement = document.createElement('div');
        styleElement.id = 'bridge-analytics-styles';
        styleElement.innerHTML = analyticsStyles;
        document.head.appendChild(styleElement);
    }
});