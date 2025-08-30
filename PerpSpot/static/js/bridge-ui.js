/**
 * Bridge Arbitrage UX Module
 * 
 * Provides seamless cross-protocol arbitrage interface with:
 * - Simplified UX mode toggle
 * - Real-time execution simulation
 * - Template management
 * - One-click unified execution analysis
 */

class BridgeArbitrageUI {
    constructor() {
        this.isSimplifiedMode = true;
        this.currentTemplate = null;
        this.simulationData = null;
        this.analyticsData = null;
        
        this.initializeUI();
        this.bindEvents();
        this.startPolling();
    }

    initializeUI() {
        // Create bridge UI container
        const bridgeContainer = document.createElement('div');
        bridgeContainer.id = 'bridge-arbitrage-container';
        bridgeContainer.className = 'bridge-container';
        bridgeContainer.innerHTML = this.getBridgeHTML();
        
        // Insert after opportunities table or at end of main content
        const opportunitiesTable = document.querySelector('#opportunities-table');
        if (opportunitiesTable) {
            opportunitiesTable.parentNode.insertBefore(bridgeContainer, opportunitiesTable.nextSibling);
        } else {
            document.querySelector('.container').appendChild(bridgeContainer);
        }
        
        // Initialize tooltips and components
        this.initializeTooltips();
        this.loadExecutionTemplates();
        this.loadAvailableTokens();
    }

    getBridgeHTML() {
        return `
            <div class="card bridge-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">
                        <i class="fas fa-bridge text-primary me-2"></i>
                        Cross-Protocol Arbitrage Bridge
                    </h5>
                    <div class="bridge-controls">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="simplifiedModeToggle" ${this.isSimplifiedMode ? 'checked' : ''}>
                            <label class="form-check-label" for="simplifiedModeToggle">
                                Simplified UX
                            </label>
                        </div>
                        <button class="btn btn-sm btn-outline-success ms-2" id="unifiedExecutionBtn">
                            <i class="fas fa-bolt"></i> Unified Analysis
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <!-- Simplified Mode View -->
                    <div id="simplifiedView" class="bridge-view ${this.isSimplifiedMode ? '' : 'd-none'}">
                        <div class="row">
                            <div class="col-md-8">
                                <div class="bridge-signals">
                                    <div class="row">
                                        <div class="col-md-3">
                                            <div class="signal-card entry-signal">
                                                <div class="signal-label">Entry Signal</div>
                                                <div class="signal-value" id="entrySignal">-</div>
                                            </div>
                                        </div>
                                        <div class="col-md-3">
                                            <div class="signal-card profit-signal">
                                                <div class="signal-label">Profit Potential</div>
                                                <div class="signal-value" id="profitPotential">0.00%</div>
                                            </div>
                                        </div>
                                        <div class="col-md-3">
                                            <div class="signal-card time-signal">
                                                <div class="signal-label">Execution Time</div>
                                                <div class="signal-value" id="executionTime">0.0s</div>
                                            </div>
                                        </div>
                                        <div class="col-md-3">
                                            <div class="signal-card confidence-signal">
                                                <div class="signal-label">Confidence</div>
                                                <div class="signal-value" id="confidenceScore">0%</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="bridge-action">
                                    <button class="btn btn-lg btn-success w-100" id="executeSimulationBtn">
                                        <i class="fas fa-play"></i> Execute Simulation
                                    </button>
                                    <small class="text-muted mt-2 d-block">
                                        Risk-adjusted analysis with latency modeling
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Advanced Mode View -->
                    <div id="advancedView" class="bridge-view ${!this.isSimplifiedMode ? '' : 'd-none'}">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="form-group mb-3">
                                    <label for="bridgeToken" class="form-label">Token Pair</label>
                                    <select class="form-select" id="bridgeToken">
                                        <option value="SOL">SOL-USDC</option>
                                        <option value="ETH">ETH-USDC</option>
                                        <option value="BTC">BTC-USDC</option>
                                        <option value="JUP">JUP-USDC</option>
                                        <option value="BONK">BONK-USDC</option>
                                        <option value="ORCA">ORCA-USDC</option>
                                    </select>
                                </div>
                                
                                <div class="form-group mb-3">
                                    <label for="bridgeSize" class="form-label">Trade Size (USD)</label>
                                    <input type="number" class="form-control" id="bridgeSize" value="1000" min="100" max="100000" step="100">
                                </div>
                                
                                <div class="form-group mb-3">
                                    <label for="executionTemplate" class="form-label">Execution Template</label>
                                    <select class="form-select" id="executionTemplate">
                                        <option value="">Select template...</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="col-md-6">
                                <div class="execution-preview" id="executionPreview">
                                    <h6>Execution Preview</h6>
                                    <div class="preview-content">
                                        <p class="text-muted">Configure parameters to see execution preview</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mt-3">
                            <div class="col-12">
                                <div class="btn-group w-100">
                                    <button class="btn btn-primary" id="simulateAdvancedBtn">
                                        <i class="fas fa-calculator"></i> Simulate Execution
                                    </button>
                                    <button class="btn btn-info" id="bridgeAnalyticsBtn">
                                        <i class="fas fa-chart-line"></i> Analytics
                                    </button>
                                    <button class="btn btn-secondary" id="saveTemplateBtn">
                                        <i class="fas fa-save"></i> Save Template
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Results Section -->
                    <div id="bridgeResults" class="bridge-results mt-4" style="display: none;">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Simulation Results</h6>
                            </div>
                            <div class="card-body" id="resultsContent">
                                <!-- Results will be populated here -->
                            </div>
                        </div>
                    </div>

                    <!-- Analytics Dashboard -->
                    <div id="bridgeAnalytics" class="bridge-analytics mt-4" style="display: none;">
                        <div class="row">
                            <div class="col-md-6">
                                <canvas id="spreadHistoryChart"></canvas>
                            </div>
                            <div class="col-md-6">
                                <canvas id="profitabilityChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        // Simplified mode toggle
        document.getElementById('simplifiedModeToggle').addEventListener('change', (e) => {
            this.isSimplifiedMode = e.target.checked;
            this.toggleViewMode();
        });

        // Unified execution analysis
        document.getElementById('unifiedExecutionBtn').addEventListener('click', () => {
            this.runUnifiedAnalysis();
        });

        // Execute simulation (simplified mode)
        document.getElementById('executeSimulationBtn').addEventListener('click', () => {
            this.executeSimulation();
        });

        // Advanced mode controls
        document.getElementById('simulateAdvancedBtn').addEventListener('click', () => {
            this.runAdvancedSimulation();
        });

        document.getElementById('bridgeAnalyticsBtn').addEventListener('click', () => {
            const selectedToken = document.getElementById('bridgeToken')?.value || 'SOL';
            this.loadBridgeAnalytics(selectedToken);
        });

        document.getElementById('saveTemplateBtn').addEventListener('click', () => {
            this.saveCurrentTemplate();
        });

        // Parameter changes
        ['bridgeToken', 'bridgeSize', 'executionTemplate'].forEach(id => {
            document.getElementById(id).addEventListener('change', () => {
                this.updateExecutionPreview();
                
                // Auto-refresh analytics when token changes
                if (id === 'bridgeToken') {
                    const analyticsSection = document.getElementById('bridgeAnalytics');
                    if (analyticsSection && analyticsSection.style.display !== 'none') {
                        const selectedToken = document.getElementById('bridgeToken').value;
                        this.loadBridgeAnalytics(selectedToken);
                    }
                }
            });
        });
    }

    toggleViewMode() {
        const simplifiedView = document.getElementById('simplifiedView');
        const advancedView = document.getElementById('advancedView');
        
        if (this.isSimplifiedMode) {
            simplifiedView.classList.remove('d-none');
            advancedView.classList.add('d-none');
        } else {
            simplifiedView.classList.add('d-none');
            advancedView.classList.remove('d-none');
        }
    }

    async runUnifiedAnalysis() {
        try {
            const btn = document.getElementById('unifiedExecutionBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

            const response = await fetch('/api/bridge/unified-execution');
            const data = await response.json();

            if (data.success && data.data.unified_analysis) {
                this.displayUnifiedResults(data.data);
            } else {
                this.showAlert('No viable opportunities found for unified execution', 'warning');
            }
        } catch (error) {
            console.error('Unified analysis error:', error);
            this.showAlert('Failed to run unified analysis', 'danger');
        } finally {
            const btn = document.getElementById('unifiedExecutionBtn');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-bolt"></i> Unified Analysis';
        }
    }

    displayUnifiedResults(data) {
        const summary = data.unified_analysis;
        const opportunities = data.detailed_opportunities;
        
        // Update simplified signals with best opportunity
        if (opportunities && opportunities.length > 0) {
            const best = opportunities[0];
            this.updateSimplifiedSignals({
                entry_signal: best.simplified_signals.entry_signal,
                profit_potential: best.simplified_signals.profit_potential,
                execution_time: best.simplified_signals.execution_time,
                confidence: best.simplified_signals.confidence
            });
        }

        // Show detailed results
        const resultsHtml = `
            <div class="unified-results">
                <div class="row">
                    <div class="col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">${summary.total_opportunities_analyzed}</div>
                            <div class="metric-label">Opportunities</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">$${summary.total_potential_profit_usd?.toFixed(2) || '0.00'}</div>
                            <div class="metric-label">Total Profit</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-card">
                            <div class="metric-value">${summary.average_confidence_percent?.toFixed(1) || '0.0'}%</div>
                            <div class="metric-label">Avg Confidence</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="metric-card">
                            <div class="metric-value action-${summary.recommended_action?.toLowerCase() || 'wait'}">${summary.recommended_action || 'WAIT'}</div>
                            <div class="metric-label">Recommendation</div>
                        </div>
                    </div>
                </div>
                
                ${opportunities.length > 0 ? `
                <div class="opportunities-list mt-4">
                    <h6>Top Opportunities</h6>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Token</th>
                                    <th>Signal</th>
                                    <th>Profit %</th>
                                    <th>Exec Time</th>
                                    <th>Confidence</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${opportunities.map(opp => `
                                    <tr>
                                        <td><strong>${opp.token}</strong></td>
                                        <td><span class="badge bg-${opp.simplified_signals.entry_signal === 'BUY' ? 'success' : 'danger'}">${opp.simplified_signals.entry_signal}</span></td>
                                        <td>${opp.simplified_signals.profit_potential?.toFixed(3) || '0.000'}%</td>
                                        <td>${opp.simplified_signals.execution_time?.toFixed(2) || '0.00'}s</td>
                                        <td>${opp.simplified_signals.confidence?.toFixed(1) || '0.0'}%</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        document.getElementById('resultsContent').innerHTML = resultsHtml;
        document.getElementById('bridgeResults').style.display = 'block';
    }

    updateSimplifiedSignals(signals) {
        document.getElementById('entrySignal').textContent = signals.entry_signal;
        document.getElementById('profitPotential').textContent = `${signals.profit_potential?.toFixed(3) || '0.000'}%`;
        document.getElementById('executionTime').textContent = `${signals.execution_time?.toFixed(2) || '0.00'}s`;
        document.getElementById('confidenceScore').textContent = `${signals.confidence?.toFixed(1) || '0.0'}%`;
        
        // Update signal card colors
        const entryCard = document.querySelector('.entry-signal');
        entryCard.className = `signal-card entry-signal ${signals.entry_signal?.toLowerCase() || ''}`;
        
        const confidenceCard = document.querySelector('.confidence-signal');
        const confidenceLevel = signals.confidence || 0;
        let confidenceClass = 'low';
        if (confidenceLevel >= 70) confidenceClass = 'high';
        else if (confidenceLevel >= 40) confidenceClass = 'medium';
        confidenceCard.className = `signal-card confidence-signal ${confidenceClass}`;
    }

    async executeSimulation() {
        try {
            const btn = document.getElementById('executeSimulationBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating...';

            // Try to get best current opportunity, use fallback if not available
            let token = 'SOL';  // Default fallback
            
            try {
                const oppsResponse = await fetch('/api/arbitrage');
                const oppsData = await oppsResponse.json();
                
                console.log('Arbitrage API Response:', oppsData);
                
                if (oppsData.success && oppsData.data && oppsData.data.length > 0) {
                    token = oppsData.data[0].token;
                    console.log('Using token from opportunity:', token);
                } else {
                    console.log('No opportunities found, using fallback token:', token);
                }
            } catch (oppsError) {
                console.log('Using fallback token due to arbitrage API error:', oppsError);
            }

            // Run simulation with guaranteed parameters
            const url = `/api/bridge/simulate?token=${token}&notional=1000`;
            console.log('Simplified simulation URL:', url);
            
            const response = await fetch(url);
            const data = await response.json();

            console.log('Simplified API Response:', data);

            if (data.success) {
                this.displaySimulationResults(data);  // Pass the full response, not data.data
            } else {
                this.showAlert('Simulation failed: ' + data.error, 'danger');
            }
        } catch (error) {
            console.error('Simulation error:', error);
            this.showAlert('Failed to run simulation', 'danger');
        } finally {
            const btn = document.getElementById('executeSimulationBtn');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-play"></i> Execute Simulation';
            }
        }
    }

    // Update execution preview when parameters change
    updateExecutionPreview() {
        const token = document.getElementById('bridgeToken')?.value || 'SOL';
        const size = document.getElementById('bridgeSize')?.value || 1000;
        const template = document.getElementById('executionTemplate')?.value;
        
        const previewElement = document.getElementById('executionPreview');
        if (!previewElement) return;
        
        // Update preview content
        const previewContent = previewElement.querySelector('.preview-content');
        if (previewContent) {
            previewContent.innerHTML = `
                <div class="preview-summary">
                    <h6>Execution Configuration</h6>
                    <div class="preview-item">
                        <span class="label">Token:</span>
                        <span class="value">${token}-USDC</span>
                    </div>
                    <div class="preview-item">
                        <span class="label">Size:</span>
                        <span class="value">$${Number(size).toLocaleString()}</span>
                    </div>
                    <div class="preview-item">
                        <span class="label">Template:</span>
                        <span class="value">${template || 'Auto-selected'}</span>
                    </div>
                </div>
                <div class="preview-actions">
                    <button class="btn btn-primary btn-sm w-100" onclick="bridgeUI.runAdvancedSimulation()">
                        <i class="fas fa-play"></i> Run Simulation
                    </button>
                </div>
            `;
        }
    }

    displaySimulationResults(simulation) {
        console.log('Displaying simulation results:', simulation);
        
        // Extract data from actual API response format
        const stats = simulation.simulation_stats || {};
        const params = simulation.input_parameters || {};
        const metadata = simulation.execution_metadata || {};
        
        const isViable = stats.success_probability > 0.6 && stats.mean_pnl > 0;
        const avgLatencyMs = stats.avg_exec_ms || 0;
        const avgLatencyS = avgLatencyMs / 1000;
        
        const resultsHtml = `
            <div class="simulation-results">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Monte Carlo Simulation Results</h6>
                        <div class="analysis-metrics">
                            <div class="metric">
                                <span class="label">Mean PnL:</span>
                                <span class="value ${stats.mean_pnl > 0 ? 'positive' : 'negative'}">
                                    $${stats.mean_pnl?.toFixed(2) || '0.00'}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="label">Success Probability:</span>
                                <span class="value">${(stats.success_probability * 100)?.toFixed(1) || '0.0'}%</span>
                            </div>
                            <div class="metric">
                                <span class="label">Average Execution Time:</span>
                                <span class="value">${avgLatencyS?.toFixed(2)}s</span>
                            </div>
                            <div class="metric">
                                <span class="label">Sharpe Ratio:</span>
                                <span class="value">${stats.sharpe_ratio?.toFixed(3) || '0.000'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">95th Percentile PnL:</span>
                                <span class="value ${stats.pnl_95pctile > 0 ? 'positive' : 'negative'}">
                                    $${stats.pnl_95pctile?.toFixed(2) || '0.00'}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="label">5th Percentile PnL:</span>
                                <span class="value ${stats.pnl_5pctile > 0 ? 'positive' : 'negative'}">
                                    $${stats.pnl_5pctile?.toFixed(2) || '0.00'}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6>Simulation Parameters</h6>
                        <div class="analysis-metrics">
                            <div class="metric">
                                <span class="label">Token:</span>
                                <span class="value">${params.token || 'N/A'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Notional Size:</span>
                                <span class="value">$${params.notional_usd?.toLocaleString() || '0'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Spread:</span>
                                <span class="value">${params.spread_bps || '0'} bps</span>
                            </div>
                            <div class="metric">
                                <span class="label">Jupiter Price:</span>
                                <span class="value">$${params.jupiter_price || '0'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Hyperliquid Price:</span>
                                <span class="value">$${params.hyperliquid_price || '0'}</span>
                            </div>
                            <div class="metric">
                                <span class="label">Simulations:</span>
                                <span class="value">${stats.n_simulations?.toLocaleString() || '0'}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="viability-indicator ${isViable ? 'viable' : 'not-viable'}">
                            <i class="fas fa-${isViable ? 'check-circle' : 'times-circle'}"></i>
                            ${isViable ? 'Execution Viable - Profitable with Good Success Rate' : 'Not Currently Viable - Low Profitability or Success Rate'}
                        </div>
                    </div>
                </div>
                
                ${stats.sample_draws && stats.sample_draws.length > 0 ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Sample Simulation Runs</h6>
                        <div class="sample-runs">
                            ${stats.sample_draws.slice(0, 5).map((draw, index) => `
                                <div class="sample-run ${draw.success ? 'success' : 'failed'}">
                                    <span class="run-number">#${index + 1}</span>
                                    <span class="run-time">${(draw.exec_time_ms / 1000).toFixed(2)}s</span>
                                    <span class="run-pnl ${draw.pnl_usd > 0 ? 'positive' : 'negative'}">
                                        $${draw.pnl_usd.toFixed(2)}
                                    </span>
                                    <span class="run-status">${draw.success ? '✓' : '✗'}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        document.getElementById('resultsContent').innerHTML = resultsHtml;
        document.getElementById('bridgeResults').style.display = 'block';
    }

    async runAdvancedSimulation() {
        try {
            const btn = document.getElementById('simulateAdvancedBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating...';

            // Get form elements with error checking
            const tokenElement = document.getElementById('bridgeToken');
            const sizeElement = document.getElementById('bridgeSize');
            const templateElement = document.getElementById('executionTemplate');
            
            // Debug logging
            console.log('Form elements:', {
                tokenElement: tokenElement,
                sizeElement: sizeElement,
                templateElement: templateElement
            });

            // Get form parameters with fallbacks and validation
            const token = tokenElement ? (tokenElement.value || 'SOL') : 'SOL';
            const sizeValue = sizeElement ? parseFloat(sizeElement.value) : 1000;
            const size = Math.max(sizeValue || 1000, 100);  // Ensure positive value
            const template = templateElement ? (templateElement.value || '') : '';

            console.log('Parameters:', { token, size, template });

            // Make API call with correct parameter name
            const url = `/api/bridge/simulate?token=${token}&notional=${size}&template=${template}`;
            console.log('API URL:', url);
            
            const response = await fetch(url);
            const data = await response.json();

            console.log('API Response:', data);

            if (data.success) {
                this.displaySimulationResults(data);  // Pass the full response, not data.data
            } else {
                this.showAlert('Simulation failed: ' + data.error, 'danger');
            }
        } catch (error) {
            console.error('Advanced simulation error:', error);
            this.showAlert('Failed to run advanced simulation', 'danger');
        } finally {
            const btn = document.getElementById('simulateAdvancedBtn');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-play"></i> Run Simulation';
            }
        }
    }

    async loadExecutionTemplates() {
        try {
            const response = await fetch('/api/bridge/templates');
            const data = await response.json();
            
            if (data.success) {
                const select = document.getElementById('executionTemplate');
                select.innerHTML = '<option value="">Select template...</option>';
                
                data.data.forEach(template => {
                    const option = document.createElement('option');
                    option.value = template.name;
                    option.textContent = `${template.name} (${template.token_pair})`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }

    async loadAvailableTokens() {
        try {
            // Use a predefined list of supported tokens as backup
            const supportedTokens = ['SOL', 'ETH', 'BTC', 'JUP', 'BONK', 'ORCA'];
            const tokenSelect = document.getElementById('bridgeToken');
            
            if (!tokenSelect) return;
            
            // Clear existing options
            tokenSelect.innerHTML = '';
            
            // Add all supported tokens
            supportedTokens.forEach(token => {
                const option = document.createElement('option');
                option.value = token;
                option.textContent = `${token}-USDC`;
                tokenSelect.appendChild(option);
            });
            
            // Try to get real-time token availability
            try {
                const response = await fetch('/api/prices');
                const data = await response.json();
                
                if (data.success && data.data) {
                    // Update the dropdown with live tokens if available
                    const liveTokens = Object.keys(data.data);
                    if (liveTokens.length > 0) {
                        tokenSelect.innerHTML = '';
                        liveTokens.forEach(token => {
                            const option = document.createElement('option');
                            option.value = token;
                            option.textContent = `${token}-USDC`;
                            tokenSelect.appendChild(option);
                        });
                    }
                }
            } catch (apiError) {
                console.log('Using fallback token list:', apiError);
            }
        } catch (error) {
            console.error('Failed to load available tokens:', error);
        }
    }

    initializeTooltips() {
        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
                new bootstrap.Tooltip(el);
            });
        }
    }

    showAlert(message, type = 'info') {
        // Create and show alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.getElementById('bridge-arbitrage-container');
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    startPolling() {
        // Poll unified analysis every 5 seconds in simplified mode
        setInterval(() => {
            if (this.isSimplifiedMode) {
                this.runUnifiedAnalysis();
            }
        }, 5000);
    }
}

// CSS Styles for Bridge UI
const bridgeStyles = `
<style>
.bridge-container {
    margin: 1rem 0;
}

.bridge-card {
    border: 1px solid #dee2e6;
    border-radius: 0.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.bridge-card .card-header {
    background: rgba(255,255,255,0.1);
    border-bottom: 1px solid rgba(255,255,255,0.2);
}

.bridge-card .card-body {
    background: rgba(255,255,255,0.05);
}

.signal-card {
    background: rgba(255,255,255,0.1);
    border-radius: 0.375rem;
    padding: 1rem;
    text-align: center;
    margin-bottom: 1rem;
    border: 1px solid rgba(255,255,255,0.2);
}

.signal-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    opacity: 0.8;
    margin-bottom: 0.25rem;
}

.signal-value {
    font-size: 1.25rem;
    font-weight: bold;
}

.entry-signal.buy .signal-value {
    color: #28a745;
}

.entry-signal.sell .signal-value {
    color: #dc3545;
}

.confidence-signal.high .signal-value {
    color: #28a745;
}

.confidence-signal.medium .signal-value {
    color: #ffc107;
}

.confidence-signal.low .signal-value {
    color: #dc3545;
}

.bridge-action {
    text-align: center;
}

.execution-preview {
    background: rgba(255,255,255,0.1);
    border-radius: 0.375rem;
    padding: 1rem;
    min-height: 200px;
}

.metric-card {
    background: rgba(255,255,255,0.1);
    border-radius: 0.375rem;
    padding: 1rem;
    text-align: center;
    margin-bottom: 1rem;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    margin-bottom: 0.25rem;
}

.metric-label {
    font-size: 0.875rem;
    opacity: 0.8;
}

.action-execute {
    color: #28a745;
}

.action-monitor {
    color: #ffc107;
}

.action-wait {
    color: #6c757d;
}

.step {
    display: flex;
    align-items: flex-start;
    margin-bottom: 1rem;
}

.step-number {
    background: #007bff;
    color: white;
    border-radius: 50%;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    margin-right: 1rem;
    flex-shrink: 0;
}

.step-content {
    flex: 1;
}

.step-action {
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.step-details {
    font-size: 0.875rem;
    opacity: 0.8;
}

.viability-indicator {
    text-align: center;
    padding: 1rem;
    border-radius: 0.375rem;
    font-weight: bold;
}

.viability-indicator.viable {
    background: rgba(40, 167, 69, 0.2);
    color: #28a745;
    border: 1px solid #28a745;
}

.viability-indicator.not-viable {
    background: rgba(220, 53, 69, 0.2);
    color: #dc3545;
    border: 1px solid #dc3545;
}

.analysis-metrics .metric {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.analysis-metrics .metric:last-child {
    border-bottom: none;
}

.value.positive {
    color: #28a745;
}

.value.negative {
    color: #dc3545;
}

.sample-runs {
    display: grid;
    gap: 0.5rem;
}

.sample-run {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-radius: 0.375rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.sample-run.success {
    border-color: rgba(40, 167, 69, 0.3);
    background: rgba(40, 167, 69, 0.1);
}

.sample-run.failed {
    border-color: rgba(220, 53, 69, 0.3);
    background: rgba(220, 53, 69, 0.1);
}

.run-number {
    font-weight: bold;
    opacity: 0.7;
    font-size: 0.875rem;
}

.run-time {
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
}

.run-pnl {
    font-weight: bold;
    font-family: 'Courier New', monospace;
}

.run-status {
    font-size: 1.25rem;
    font-weight: bold;
}

.simulation-results h6 {
    color: #007bff;
    border-bottom: 2px solid rgba(0, 123, 255, 0.2);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}

.analysis-metrics {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 0.375rem;
    padding: 1rem;
}
</style>
`;

// Initialize Bridge UI when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add CSS
    document.head.insertAdjacentHTML('beforeend', bridgeStyles);
    
    // Initialize Bridge UI
    window.bridgeArbitrageUI = new BridgeArbitrageUI();
});

// Export for external use
window.BridgeArbitrageUI = BridgeArbitrageUI;