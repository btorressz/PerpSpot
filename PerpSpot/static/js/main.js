// Main initialization file for Crypto Arbitrage Platform
// This file handles application initialization and global utilities

(function() {
    'use strict';
    
    // Global application state
    window.CryptoArbitrageApp = {
        initialized: false,
        version: '1.0.0',
        debug: true,
        services: {
            jupiter: 'operational',
            hyperliquid: 'operational',
            fallback: 'standby'
        }
    };
    
    // Initialize application when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeApplication();
    });
    
    function initializeApplication() {
        console.log('🚀 Initializing Crypto Arbitrage Platform v' + window.CryptoArbitrageApp.version);
        
        // Initialize Bootstrap tooltips
        initializeTooltips();
        
        // Initialize error handling
        initializeErrorHandling();
        
        // Initialize performance monitoring
        initializePerformanceMonitoring();
        
        // Initialize accessibility features
        initializeAccessibility();
        
        // Mark as initialized
        window.CryptoArbitrageApp.initialized = true;
        
        console.log('✅ Crypto Arbitrage Platform initialized successfully');
        
        // Emit custom event for other modules
        window.dispatchEvent(new CustomEvent('CryptoArbitrageApp:initialized', {
            detail: { version: window.CryptoArbitrageApp.version }
        }));
    }
    
    function initializeTooltips() {
        // Initialize Bootstrap tooltips for all elements with data-bs-toggle="tooltip"
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Add tooltips to specific elements
        addCustomTooltips();
    }
    
    function addCustomTooltips() {
        // Add tooltip to connection status
        const connectionStatus = document.getElementById('connection-status');
        if (connectionStatus) {
            connectionStatus.setAttribute('data-bs-toggle', 'tooltip');
            connectionStatus.setAttribute('data-bs-placement', 'bottom');
            connectionStatus.setAttribute('title', 'Real-time connection status to trading APIs');
            new bootstrap.Tooltip(connectionStatus);
        }
        
        // Add tooltips to price cards
        const priceCards = document.querySelectorAll('.price-card');
        priceCards.forEach(card => {
            const source = card.querySelector('.price-source');
            if (source) {
                const text = source.textContent;
                let tooltip = '';
                
                if (text.includes('Jupiter')) {
                    tooltip = 'Live spot prices from Jupiter DEX aggregator';
                } else if (text.includes('Hyperliquid')) {
                    tooltip = 'Perpetual futures prices from Hyperliquid exchange';
                } else if (text.includes('Spread')) {
                    tooltip = 'Price difference between spot and perpetual markets';
                }
                
                if (tooltip) {
                    card.setAttribute('data-bs-toggle', 'tooltip');
                    card.setAttribute('data-bs-placement', 'top');
                    card.setAttribute('title', tooltip);
                    new bootstrap.Tooltip(card);
                }
            }
        });
    }
    
    function initializeErrorHandling() {
        // Global error handler
        window.addEventListener('error', function(event) {
            console.error('🚨 Global error:', event.error);
            
            if (window.CryptoArbitrageApp.debug) {
                showErrorNotification('An unexpected error occurred. Check console for details.');
            }
        });
        
        // Unhandled promise rejection handler
        window.addEventListener('unhandledrejection', function(event) {
            console.error('🚨 Unhandled promise rejection:', event.reason);
            
            if (window.CryptoArbitrageApp.debug) {
                showErrorNotification('A network request failed. Please check your connection.');
            }
        });
    }
    
    function initializePerformanceMonitoring() {
        // Monitor page load performance
        window.addEventListener('load', function() {
            if ('performance' in window) {
                const perfData = performance.getEntriesByType('navigation')[0];
                const loadTime = perfData.loadEventEnd - perfData.loadEventStart;
                
                console.log(`📊 Page load time: ${loadTime}ms`);
                
                // Log performance metrics
                if (window.CryptoArbitrageApp.debug) {
                    console.log('Performance metrics:', {
                        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                        loadComplete: loadTime,
                        firstPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-paint')?.startTime || 0,
                        firstContentfulPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-contentful-paint')?.startTime || 0
                    });
                }
            }
        });
    }
    
    function initializeAccessibility() {
        // Add skip to main content link
        addSkipToMainLink();
        
        // Initialize keyboard navigation enhancements
        initializeKeyboardNavigation();
        
        // Add ARIA labels to dynamic content
        addAriaLabels();
    }
    
    function addSkipToMainLink() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'sr-only sr-only-focusable btn btn-primary position-absolute';
        skipLink.style.top = '10px';
        skipLink.style.left = '10px';
        skipLink.style.zIndex = '9999';
        skipLink.textContent = 'Skip to main content';
        
        document.body.insertBefore(skipLink, document.body.firstChild);
        
        // Add main content landmark if it doesn't exist
        const mainContent = document.querySelector('main, [role="main"], #main-content');
        if (!mainContent) {
            const container = document.querySelector('.container-fluid');
            if (container) {
                container.setAttribute('id', 'main-content');
                container.setAttribute('role', 'main');
            }
        }
    }
    
    function initializeKeyboardNavigation() {
        // Enhance table navigation
        const table = document.querySelector('.table');
        if (table) {
            table.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    const button = event.target.querySelector('button');
                    if (button) {
                        event.preventDefault();
                        button.click();
                    }
                }
            });
        }
        
        // Enhance trading mode selection with arrow keys
        const tradingModeGroup = document.getElementById('trading-mode-group');
        if (tradingModeGroup) {
            tradingModeGroup.addEventListener('keydown', function(event) {
                const inputs = tradingModeGroup.querySelectorAll('input[type="radio"]');
                const currentIndex = Array.from(inputs).findIndex(input => input.checked);
                
                if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
                    event.preventDefault();
                    const prevIndex = (currentIndex - 1 + inputs.length) % inputs.length;
                    inputs[prevIndex].checked = true;
                    inputs[prevIndex].dispatchEvent(new Event('change'));
                } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
                    event.preventDefault();
                    const nextIndex = (currentIndex + 1) % inputs.length;
                    inputs[nextIndex].checked = true;
                    inputs[nextIndex].dispatchEvent(new Event('change'));
                }
            });
        }
    }
    
    function addAriaLabels() {
        // Add ARIA labels to price displays
        const priceElements = document.querySelectorAll('.price-value');
        priceElements.forEach(element => {
            if (!element.getAttribute('aria-label')) {
                const card = element.closest('.price-card');
                const source = card?.querySelector('.price-source')?.textContent || 'Price';
                element.setAttribute('aria-label', `${source} value`);
            }
        });
        
        // Add ARIA labels to spread indicators
        const spreadElement = document.getElementById('spread-value');
        if (spreadElement) {
            spreadElement.setAttribute('aria-label', 'Price spread percentage');
        }
        
        // Add ARIA labels to opportunity table buttons
        const tableButtons = document.querySelectorAll('.table button');
        tableButtons.forEach(button => {
            if (!button.getAttribute('aria-label')) {
                const row = button.closest('tr');
                const token = row?.querySelector('td:first-child strong')?.textContent || 'token';
                button.setAttribute('aria-label', `Analyze ${token} arbitrage opportunity`);
            }
        });
    }
    
    // Utility functions
    function showErrorNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 end-0 m-3';
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    // Export utility functions to global scope
    window.CryptoArbitrageApp.utils = {
        showErrorNotification: showErrorNotification,
        formatNumber: function(num, decimals = 2) {
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
        },
        formatPercentage: function(num, decimals = 2) {
            if (num === null || num === undefined || isNaN(num)) return '--%';
            return `${num.toFixed(decimals)}%`;
        },
        formatCurrency: function(num, decimals = 2) {
            if (num === null || num === undefined || isNaN(num)) return '$--';
            return `$${window.CryptoArbitrageApp.utils.formatNumber(num, decimals)}`;
        }
    };
    
    // Development helpers
    if (window.CryptoArbitrageApp.debug) {
        window.debugApp = function() {
            console.log('🔍 Debug info:', {
                initialized: window.CryptoArbitrageApp.initialized,
                version: window.CryptoArbitrageApp.version,
                services: window.CryptoArbitrageApp.services,
                performance: performance.getEntriesByType('navigation')[0]
            });
        };
        
        console.log('💡 Debug mode enabled. Use debugApp() to view application state.');
    }
    
})();
