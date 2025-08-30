# Perp Spot - Crypto Arbitrage Platform

## Overview 

A sophisticated cryptocurrency perpetuals arbitrage trading platform called "Perp Spot Crypto Arbitrage" that bridges Jupiter spot trading with Hyperliquid perpetual futures. Features real-time WebSocket data feeds with mainnet/testnet fallback, arbitrage opportunity detection, interactive dashboard with Chart.js visualization, execution latency modeling, Monte Carlo simulation modeling, advanced slippage management with standardized color-coded visualization (Green ≤50bps, Orange 50-200bps, Red >200bps), comprehensive analytics including Z-score spread detection and VaR calculations, Redis-backed caching, trading simulation capabilities, and dynamic token discovery supporting around 10 cryptocurrency pairs.(plan to add 100+ in next version)

**NOTE** I am still reviewing and developing this project feedback is welcome, this is the first version it won't be perfect, but it runs.

---


## 🚀 Features

- **Real-time WebSocket Streaming**: Live price feeds with mainnet (`wss://api.hyperliquid.xyz/ws`) as primary and testnet (`wss://api.hyperliquid-testnet.xyz/ws`) as fallback
- **Arbitrage Detection**: Automated detection of profitable trading opportunities between spot and perpetual markets with Z-score spread analysis
- **Cross-Protocol Bridge**: Seamless execution modeling between Jupiter spot and Hyperliquid perpetuals with Monte Carlo simulation and VaR calculations
- **Dynamic Token Discovery**: Supports 100+ cryptocurrency pairs with automatic token discovery and validation
- **Standardized Slippage Visualization**: Color-coded system (Green ≤50bps, Orange 50-200bps, Red >200bps) applied consistently across all UI elements
- **Interactive Dashboard**: Real-time Chart.js visualizations with WebSocket-powered live updates
- **Execution Templates**: Pre-configured strategies (SOL Scalping, ETH Conservative, BTC Large Size) with Monte Carlo risk modeling
- **Redis Caching**: High-performance caching with automatic failover to local cache
- **Advanced Analytics**: Volume, profitability, latency, and spread analysis with pandas DataFrames and Sharpe ratio calculations
- **Robust Failover System**: Mainnet WebSocket → Testnet WebSocket → REST API → CoinGecko/Kraken fallback chain
- **WebSocket Connection Management**: Automatic reconnection with exponential backoff and connection health monitoring
- **Background Processing**: APScheduler for continuous price updates with real-time WebSocket integration

---


## 📁 Project Structure

### Core Application Files

#### `app.py`
Main Flask application setup and configuration:
- **Database initialization** with SQLAlchemy ORM and DeclarativeBase
- **Flask app configuration** with proxy middleware for deployment
- **Environment variable handling** for DATABASE_URL and SESSION_SECRET
- **Background scheduler setup** using APScheduler for price updates
- **Service initialization** including arbitrage and bridge services
- **Blueprint registration** for main routes and API endpoints
- **Auto-creates database tables** on startup with proper error handling
- **Logging configuration** using custom logger utilities

#### `main.py`
Application entry point:
- **Simple Flask app import** for Gunicorn deployment
- **Development server configuration** with debug mode enabled
- **Minimal wrapper** that allows the application to run standalone

#### `models.py`
Database models using SQLAlchemy ORM:

##### **PriceData Model**
- **Historical price storage** with token symbol, source exchange, and price type
- **Fields**: id, token, source (jupiter/hyperliquid/coingecko/kraken), price_type (spot/mark/index), price, timestamp
- **Methods**: to_dict() for JSON serialization

##### **FundingRate Model**
- **Perpetual contract funding rate tracking** with current and predicted rates
- **Fields**: id, token, funding_rate, predicted_funding_rate, timestamp
- **Used for** calculating funding costs in arbitrage strategies

##### **ArbitrageOpportunity Model**
- **Detected arbitrage opportunity storage** with spread calculations in basis points
- **Fields**: id, token, spot_price, perp_price, spread_bps, estimated_pnl, strategy, timestamp
- **Strategy types**: 'long_spot_short_perp' or 'short_spot_long_perp'

##### **SystemStatus Model**
- **Service health monitoring** with status tracking for external APIs
- **Fields**: id, service, status (online/offline/rate_limited), last_update, error_message
- **Used for** monitoring Jupiter, Hyperliquid, and fallback service health

### Services Directory (`services/`)

#### `arbitrage_service.py`
**ENHANCED:** Core arbitrage detection with real-time WebSocket integration:
- **WebSocket-First Architecture**: Prioritizes real-time WebSocket data over REST API calls
- **Price data aggregation** from multiple sources with comprehensive error handling
- **Real-time Streaming Integration**: Automatically enables WebSocket streaming on initialization
- **Spread calculation** with standardized basis points thresholds and color coding
- **Z-score Analysis**: Advanced statistical analysis for opportunity detection
- **Opportunity detection** with configurable minimum spread thresholds (default: 30 bps)
- **Smart Fallback Chain**: WebSocket → REST API → Fallback APIs → Demo data
- **Threading safety** with locks for concurrent operations and WebSocket integration
- **Dynamic Token Support**: Expandable token list supporting 100+ cryptocurrency pairs
- **Key Methods**:
  - `enable_realtime_streaming()`: Initializes WebSocket streaming for real-time data
  - `update_all_prices()`: Coordinates price updates prioritizing WebSocket data
  - `calculate_arbitrage_opportunities()`: Identifies profitable spreads with advanced analytics
  - `_generate_demo_spot_prices()` & `_generate_demo_perp_prices()`: Realistic demo data generation

#### `hyperliquid_service.py`
**ENHANCED:** Hyperliquid perpetual futures integration with WebSocket streaming:
- **SDK Integration** using official Hyperliquid Python SDK with mainnet configuration
- **WebSocket Integration**: Real-time price streaming with automatic fallback to REST API
- **Dual Network Support**: Mainnet as primary, testnet as fallback (configurable via `HYPERLIQUID_TESTNET` env var)
- **Smart Data Sources**: Uses WebSocket data when available, falls back to REST API calls
- **Cache Integration**: WebSocket data cached with 1-second TTL for ultra-low latency access
- **Token Universe Management**: Dynamic token discovery from Hyperliquid universe metadata
- **Health Monitoring**: Connection health checks and service status monitoring
- **Key Methods**:
  - `enable_websocket_streaming()`: Initializes WebSocket listener with callback integration
  - `get_websocket_prices()`: Primary method that uses WebSocket data or falls back to REST
  - `get_perpetual_prices()`: REST API fallback for perpetual price data
  - `get_funding_rates()`: Retrieves current funding rate data with real-time updates
  - `_handle_ws_data()`: Processes incoming WebSocket data and updates local cache
  - `health_check()`: Monitors API connectivity and service availability

#### `jupiter_service.py`
Jupiter (Solana DEX) spot price integration:
- **Token mint mapping** from symbols to Solana mint addresses
- **Price API integration** using Jupiter's price aggregation API
- **Comprehensive token support** including HL token mint address
- **Volume and liquidity data** with 24h metrics
- **Rate limiting** and retry logic for API reliability
- **Key Methods**:
  - `get_spot_prices()`: Retrieves spot prices for all supported tokens
  - `_get_token_price()`: Individual token price fetching with retry logic
  - `get_token_volume()`: Fetches trading volume and liquidity metrics

#### `fallback_service.py`
Backup price sources for reliability:
- **CoinGecko integration** as primary fallback with comprehensive token ID mapping
- **Kraken integration** as secondary fallback for major trading pairs
- **HL token support** with 'hyperliquid' CoinGecko ID mapping
- **Rate limiting handling** with graceful degradation
- **Currency conversion** and price normalization
- **Key Methods**:
  - `get_coingecko_prices()`: Fetches prices from CoinGecko API
  - `get_kraken_prices()`: Fetches prices from Kraken public API
  - `normalize_price_data()`: Standardizes price format across sources

#### `slippage_model.py`
- Advanced slippage and market impact modeling:
- **Square-root impact formula**: slippage = k × sqrt(size/depth) with configurable parameters
- **Almgren-Chriss modeling**: Advanced execution cost estimation with temporary and permanent impact
- **Orderbook depth analysis** with realistic depth assumptions for different tokens
- **Configurable parameters**: k=0.7 (impact coefficient), a=0.3, b=0.6 (Almgren-Chriss parameters)
- **Monotonicity validation**: Ensures slippage increases with trade size
- **Interactive controls**: User-configurable tolerance settings and real-time estimates
- **Error handling** for edge cases and invalid inputs
- **Key Methods**:
  - `calculate_slippage()`: Main slippage calculation with square-root model
  - `estimate_market_impact()`: Almgren-Chriss style impact estimation
  - `get_orderbook_depth()`: Estimates available liquidity for each token

#### `bridge_service.py`
- Integrated Cross-Protocol Arbitrage Bridge with advanced simulation:
- **Monte Carlo simulation** with statistical modeling of execution latency
- **Risk analysis** including Value-at-Risk, Sharpe ratio, and success probability
- **Execution templates** with pre-configured strategies:
  - **SOL Scalping**: High-frequency, low-latency strategy
  - **ETH Conservative**: Risk-managed approach with lower leverage
  - **BTC Large Size**: Optimized for large volume institutional trades
- **Latency modeling** with sophisticated execution time predictions
- **Pandas integration** for advanced data analysis and historical metrics
- **JSON serialization** with safe conversion of numpy/pandas data types
- **Unified execution analysis** with one-click top 5 opportunities analysis
- **Bridge playbooks** with step-by-step JSON execution plans
- **Key Methods**:
  - `simulate_bridge_execution()`: Comprehensive Monte Carlo simulation
  - `analyze_bridge_performance()`: Historical analytics with pandas
  - `get_execution_templates()`: Template management and CRUD operations
  - `generate_execution_playbook()`: Creates detailed trading instructions

#### `cache_service.py`
- Redis-backed high-performance caching system:
- **TTL management** with 5-7 second time-to-live for fresh data
- **Graceful degradation** with full functionality when Redis is unavailable
- **API rate limiting reduction** by ~70% through intelligent caching
- **Data persistence** for frequently accessed price and analytics data
- **Thread safety** with concurrent access protection
- **Cache statistics** with hit rate monitoring and performance metrics
- **Key Methods**:
  - `get_cached_data()` & `set_cached_data()`: Core caching with TTL
  - `invalidate_cache()`: Smart cache invalidation on price movements
  - `get_cache_stats()`: Performance monitoring and analysis

#### `analytics_service.py`
Advanced analytics and calculations:
- **Spread analysis** with percentage calculations between spot and perpetual prices
- **Slippage integration** with market impact estimation
- **Risk metrics** including risk-adjusted returns and volatility calculations
- **Historical analysis** with price trend tracking and arbitrage frequency
- **Performance metrics** with profit/loss tracking and success rates

#### `polling_service.py`
Background price update coordination:
- **Scheduler integration** with APScheduler for periodic updates
- **Rate limiting management** to avoid exceeding API limits
- **Error handling** with robust retry logic and exponential backoff
- **Comprehensive logging** of all price update activities
- **Service health monitoring** with status tracking

#### `price_fetcher.py`
Unified price fetching interface:
- **Service coordination** between Jupiter, Hyperliquid, and fallback services
- **Data normalization** with standardized price format across sources
- **Cache management** with intelligent caching strategies
- **Error aggregation** and centralized error handling

#### `ws_listener.py`
**ENHANCED:** Real-time WebSocket streaming with mainnet/testnet fallback:
- **Dual WebSocket URLs**: Mainnet (`wss://api.hyperliquid.xyz/ws`) as primary, testnet (`wss://api.hyperliquid-testnet.xyz/ws`) as fallback
- **Smart Failover Logic**: Automatically switches to testnet after 3 mainnet connection failures
- **Subscription Management**: Subscribes to `allMids`, `l1Book`, `trades`, and `meta` channels for comprehensive data
- **Real-time Price Processing**: Processes live price updates, funding rates, and volume data
- **Connection Health Monitoring**: Ping/pong handling with configurable timeouts (20s ping interval, 10s timeout)
- **Automatic Reconnection**: Exponential backoff with maximum retry limits (10 attempts per network)
- **Background Thread Management**: Proper event loop handling with signal processing for graceful shutdown
- **Data Callbacks**: Extensible callback system for real-time data processing and cache updates
- **Network Resilience**: Handles connection drops, network issues, and API failures gracefully
- **Key Methods**:
  - `start_background_listener()`: Starts WebSocket in dedicated background thread
  - `connect()`: Main connection logic with retry and failover handling
  - `_subscribe()`: Subscribes to all necessary Hyperliquid data channels
  - `_process_message()`: Processes incoming WebSocket messages and updates live data
  - `_handle_reconnection()`: Manages reconnection with exponential backoff

### Routes Directory (`routes/`)

#### `api.py`
RESTful API endpoints with comprehensive bridge integration:
- **GET /api/prices**: Returns current prices for all tokens with source attribution
- **GET /api/arbitrage**: Returns current arbitrage opportunities with slippage estimates
- **GET /api/market-overview**: Provides market summary statistics
- **GET /api/charts**: Returns historical data for charting with time series
- **GET /api/funding**: Returns funding rate data for perpetual contracts
- **GET /api/bridge/simulate**: Advanced bridge execution simulation with Monte Carlo modeling
- **GET /api/bridge/unified-execution**: One-click analysis of top 5 opportunities with UX signals
- **GET /api/bridge/analytics**: Comprehensive analytics dashboard with pandas-powered insights
- **GET /api/bridge/templates**: Execution template management with CRUD operations
- **GET /api/bridge/playbook**: Generates step-by-step execution instructions
- **GET /api/slippage-estimate**: Real-time slippage estimation for user-specified trade sizes
- **POST endpoints** for template management and future trade execution
- **Error handling** with comprehensive API error responses and detailed context

#### `main.py` (routes)
Main web interface routes:
- **GET /**: Main dashboard page with full template rendering
- **Static asset management** for CSS and JavaScript files
- **Template context** with dynamic data injection

### Utils Directory (`utils/`)

#### `config.py`
Centralized configuration management:
- **Environment variables** with comprehensive configuration loading
- **API settings** including timeout, retry, and rate limiting configurations
- **Trading parameters** with spread thresholds, position sizes, and notional amounts
- **Token configuration** with master list of all supported cryptocurrencies
- **Default values** with sensible defaults for all configuration options
- **Validation** with configuration validation and error checking

#### `logger.py`
Centralized logging configuration:
- **File logging** with daily rotating log files in `logs/` directory
- **Console logging** with colored output for development
- **Log levels** with configurable logging levels (DEBUG, INFO, WARNING, ERROR)
- **Formatting** with structured log format including timestamps and source information
- **Performance logging** with execution time tracking for critical operations

#### `trade_execution.py`
Trading execution utilities (future enhancement):
- **Order management** framework for automated trade execution
- **Risk management** with position sizing and risk controls
- **Execution algorithms** with smart order routing and execution strategies
- **Slippage integration** with real-time slippage calculations during execution

### Test Directory (`tests/`)

#### `test_slippage_model.py`
Comprehensive slippage model testing:
- **Unit tests** for slippage calculation accuracy and edge cases
- **Monotonicity validation** ensuring slippage increases with trade size
- **Parameter testing** with various k, a, b coefficient combinations
- **Error handling tests** for invalid inputs and edge cases
- **Performance benchmarks** for calculation speed and efficiency

#### `test_bridge_simulation.py`
Bridge service testing:
- **Monte Carlo simulation tests** with statistical validation
- **Template testing** for all execution strategies
- **Integration tests** with mock data and API responses
- **Performance testing** for simulation speed and accuracy

### Examples Directory (`examples/`)

#### `slippage_demo.py`
Demonstration script for slippage calculations:
- **Trade impact analysis** showing slippage for $1k, $10k, $100k trade sizes
- **Real-world examples** with SOL, ETH, BTC scenarios
- **Visual output** with formatted tables and impact analysis
- **Performance comparison** between different orderbook depths

### Frontend Files

#### `templates/index.html`
Main dashboard HTML template:
- **Nintendo-style design** with gradient backgrounds using Jupiter/Hyperliquid/Solana colors
- **Live price grid** with real-time price display for all 8 tokens
- **Token selection dropdown** with all supported cryptocurrencies including HL
- **Chart integration** with Chart.js for price visualization and spread analysis
- **Interactive slippage controls** with tolerance settings, progress bars, and warning alerts
- **Slippage visualization chart** showing trade size impact curves for both platforms
- **Advanced settings toggle** with expandable controls for power users
- **Responsive design** using Bootstrap 5 for mobile-friendly interface
- **Bridge integration** with embedded arbitrage bridge interface
- **Slippage display** with color-coded basis points in opportunities table

#### `static/js/app.js`
**ENHANCED:** Frontend JavaScript application with WebSocket-powered real-time updates:
- **Real-time WebSocket Integration** with live price updates flowing from WebSocket streams
- **Standardized Color Coding** for slippage visualization (Green ≤50bps, Orange 50-200bps, Red >200bps)
- **Chart management** with Chart.js price charts showing real-time WebSocket data
- **Live Data Processing** handles both WebSocket streams and API polling seamlessly
- **Interactive slippage controls** with tolerance sliders and real-time color-coded feedback
- **Dynamic Token Support** automatically adapts to new tokens from dynamic discovery
- **Smart alert system** with real-time notifications based on WebSocket price changes
- **Connection Status Monitoring** displays WebSocket connection health and fallback status
- **Multi-source Integration** handles data from mainnet/testnet WebSocket and REST APIs
- **Bridge integration** with real-time arbitrage analysis and execution simulation
- **Progressive Enhancement** gracefully handles WebSocket disconnections and API failures
- **Performance Optimization** reduces server load through efficient WebSocket data handling
- **Error handling** with comprehensive fallback chains and user notifications

#### `static/js/bridge-ui.js`
 - **Advanced** bridge arbitrage user interface:
- **Simulation controls** with token selection, size configuration, and template management
- **Results display** with comprehensive simulation results including risk metrics
- **UX mode toggle** for seamless switching between simplified and advanced views
- **Template management** with save/load functionality for execution strategies
- **Real-time integration** with auto-updates from main price feed
- **Key Features**:
  - `runUnifiedAnalysis()`: One-click analysis of top opportunities
  - `runAdvancedSimulation()`: Detailed simulation with template support
  - `displaySimulationResults()`: Rich visualization of execution analysis
  - `toggleUXMode()`: Simple/Advanced interface switching

#### `static/js/bridge-analytics.js`
 - **Enhanced analytics** dashboard functionality:
- **Analytics loading** with comprehensive performance metrics and auto-refresh
- **Data visualization** with interactive charts and performance indicators
- **Auto-scroll** with smooth scrolling to analytics section after loading
- **Token performance** with individual asset analysis and profit tracking
- **Volume metrics** including total, viable, and average trade size analysis
- **Latency analysis** with execution time statistics and 95th percentile calculations
- **Success rate tracking** with historical performance metrics and trend analysis
- **Responsive design** with mobile-optimized analytics dashboard

#### `static/css/style.css`
Custom styling:
- **Nintendo theme** with gradient backgrounds and retro gaming aesthetics
- **Color scheme** using Jupiter purple, Hyperliquid blue, Solana green
- **Interactive form controls** with custom-styled range sliders, checkboxes, and progress bars
- **Slippage control styling** with professional tolerance controls and warning alerts
- **Animations** with smooth transitions and hover effects
- **Responsive layout** with mobile-first responsive design approach
- **Slippage indicators** with color-coded basis points (green/orange/red)

---

## 🎯 Interactive Slippage Management System

The platform features a comprehensive slippage management system designed for professional traders:

### User-Configurable Controls
- **Tolerance Settings**: Adjustable slippage tolerance from 50-500 basis points
- **Real-time Estimates**: Live slippage calculations based on current trade size
- **Visual Progress Bar**: Color-coded slippage indicator (green/yellow/red)
- **Advanced Settings**: Expandable controls for experienced traders
- **Smart Alerts**: Automatic notifications when opportunities exceed your tolerance

### Interactive Visualization
- **Trade Size Impact Chart**: Shows how slippage changes from $100 to $50K trades
- **Platform Comparison**: Visual comparison of Jupiter vs Hyperliquid slippage curves
- **Tolerance Reference Line**: Your current tolerance displayed as a reference line
- **Real-time Updates**: Chart updates dynamically when you adjust tolerance settings

### Professional Features
- **Expected Slippage Display**: Shows estimated slippage for your current trade size
- **Opportunity Monitoring**: Scans all opportunities and alerts on high-slippage trades
- **Toggle Controls**: Easy enable/disable of alerts and advanced features
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## 🌉 Bridge Arbitrage System

### Slippage & Market Impact Modeling
The platform includes sophisticated slippage estimation using square-root market impact models with full user control:

#### **Square-Root Impact Formula**
```
slippage = k × sqrt(trade_size / orderbook_depth)
```
- **k = 0.7**: Impact coefficient calibrated for crypto markets
- **Realistic scaling**: 31 bps for $1k vs 313 bps for $100k SOL trades
- **Token-specific depth**: Different liquidity assumptions per asset

#### **Almgren-Chriss Style Estimation**
- **Temporary Impact**: a × (size/depth)^b with a=0.3, b=0.6
- **Permanent Impact**: Separate modeling for lasting market effects
- **Execution Cost**: Combined temporary + permanent impact estimation

### Execution Templates
Three pre-configured execution templates optimized for different trading scenarios:

#### **SOL Scalping Template**
- **Strategy**: High-frequency, low-latency arbitrage for SOL token
- **Position Size**: $500-2000 optimal range
- **Target Spread**: 15+ basis points
- **Risk Profile**: Medium-high (leverage: 3x)
- **Execution Time**: <2 seconds average
- **Use Case**: Quick scalps during high volatility periods

#### **ETH Conservative Template**  
- **Strategy**: Risk-managed approach for ETH arbitrage
- **Position Size**: $1000-5000 optimal range
- **Target Spread**: 25+ basis points
- **Risk Profile**: Low-medium (leverage: 2x)
- **Execution Time**: <4 seconds average
- **Use Case**: Steady profits with lower risk exposure

#### **BTC Large Size Template**
- **Strategy**: Optimized for large volume BTC trades
- **Position Size**: $5000-25000 optimal range
- **Target Spread**: 35+ basis points
- **Risk Profile**: Low (leverage: 1.5x)
- **Execution Time**: <6 seconds average
- **Use Case**: Institutional-level arbitrage with capital efficiency

### Monte Carlo Simulation Features
- **Latency modeling** with statistical analysis of execution delays
- **95th percentile calculations** for conservative risk assessment
- **Success probability** with confidence intervals for trade execution
- **Funding rate impact** with dynamic adjustment for perpetual costs
- **Market impact analysis** with slippage estimation based on orderbook depth

### Advanced Analytics Dashboard
- **Volume analysis** with total, viable, and average trade size breakdown
- **Latency analysis** with execution time distribution and percentile analysis
- **Token performance** with individual asset profitability and success rate tracking
- **Spread analysis** with historical patterns and viable thresholds
- **Risk metrics** including Value-at-Risk, Sharpe ratios, and funding rate impacts

## 🔧 Token Support

The platform supports 8 major cryptocurrencies with full bridge arbitrage capabilities:

| Token | Name | Jupiter Mint Address | CoinGecko ID | Hyperliquid Support | Bridge Ready |
|-------|------|---------------------|--------------|-------------------|--------------|
| SOL | Solana | So11111111111111111111111111111111111111112 | solana | ✅ | ✅ |
| ETH | Ethereum | - | ethereum | ✅ | ✅ |
| BTC | Bitcoin | - | bitcoin | ✅ | ✅ |
| JUP | Jupiter | JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN | jupiter-exchange-solana | ❌ | ✅ |
| BONK | Bonk | DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263 | bonk | ❌ | ✅ |
| ORCA | Orca | orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE | orca | ❌ | ✅ |
| USDC | USD Coin | EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v | usd-coin | ❌ | ✅ |
| USDT | Tether | Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB | tether | ❌ | ✅ |
| HL | Hyperliquid | 4Ae83YgsBcwJTMx3am3gi5Ppnp1KwmunznWAoYeqgDgL | hyperliquid | ✅ | ✅ |

**Bridge Ready**: All tokens support full bridge arbitrage simulation with execution templates and slippage modeling.

## 🏗️ Architecture

### Data Flow

#### Real-time WebSocket Pipeline
1. **WebSocket Listener** connects to Hyperliquid mainnet (`wss://api.hyperliquid.xyz/ws`)
2. **Live Data Streaming** receives real-time price updates, funding rates, and volume data
3. **Automatic Failover** switches to testnet (`wss://api.hyperliquid-testnet.xyz/ws`) if mainnet fails
4. **Cache Integration** stores WebSocket data with 1-second TTL for ultra-low latency
5. **Background Scheduler** supplements with REST API calls every 10 seconds for missing data

#### Comprehensive Fallback Chain
1. **Primary**: Hyperliquid WebSocket (Mainnet) - Real-time streaming
2. **Secondary**: Hyperliquid WebSocket (Testnet) - Fallback streaming
3. **Tertiary**: Hyperliquid REST API - Traditional API calls
4. **Quaternary**: Jupiter Service - Solana DEX spot prices
5. **Fallback**: CoinGecko/Kraken APIs - External price sources
6. **Demo Mode**: Realistic demo data for testing and development

#### Processing Pipeline
1. **Arbitrage Service** coordinates real-time price updates from WebSocket streams
2. **Slippage Model** calculates market impact estimates with standardized color coding
3. **Analytics Service** processes data with Z-score analysis and VaR calculations
4. **Cache Service** stores data with intelligent TTL management (1s for WebSocket, 5-7s for REST)
5. **Frontend** receives live updates via WebSocket integration and API polling
7. **Database** stores historical price data and arbitrage opportunities

### Fallback Strategy
1. **Primary**: Jupiter API for spot prices, Hyperliquid SDK for perpetual prices
2. **Secondary**: CoinGecko API for all token prices with comprehensive mapping
3. **Tertiary**: Kraken API for major token pairs
4. **Demo Mode**: Generated realistic price data when all APIs fail

### Error Handling
- **Retry logic** with automatic retries and exponential backoff
- **Rate limiting** respecting API limits with intelligent delays
- **Graceful degradation** falling back to demo data to maintain functionality
- **Comprehensive logging** with detailed error logging for debugging
- **Service health monitoring** with status tracking for all external services

---


## 📊 Demo Mode

When external APIs are unavailable, the platform automatically switches to demo mode:
- **Realistic prices** based on current market values with small variations
- **Arbitrage opportunities** with generated spreads to demonstrate platform functionality
- **Full functionality** including slippage calculations and bridge simulation
- **Slippage modeling** with realistic impact estimates for different trade sizes

## 🎛️ Slippage Control Features

### Interactive Controls
- **Range Slider**: Smooth adjustment of slippage tolerance from 50-500 bps
- **Live Feedback**: Real-time display of current tolerance setting
- **Expected Slippage**: Shows estimated slippage for your current trade size
- **Progress Visualization**: Color-coded progress bar showing slippage relative to tolerance
- **Advanced Toggle**: Expandable section with additional controls for power users

### Smart Warning System
- **Opportunity Scanning**: Automatically monitors all opportunities in real-time
- **Threshold Alerts**: Alerts when trades exceed your configured tolerance
- **Count Display**: Shows number of opportunities above your tolerance
- **Toggle Control**: Easy enable/disable of alert notifications
- **Visual Indicators**: Clear color coding throughout the interface

### Integration Benefits
- **Seamless UX**: Slippage controls integrate naturally with existing trading interface
- **Real-time API**: Backend `/api/slippage-estimate` endpoint for live calculations  
- **Chart Integration**: Dedicated slippage visualization chart with platform comparison
- **Mobile Responsive**: Full functionality on all device sizes
- **Professional Styling**: Clean, modern design matching platform aesthetics

## 🔄 Real-time Updates

The platform provides real-time updates through:
- **Backend polling** with price updates every 10 seconds via APScheduler
- **Frontend polling** with dashboard updates every 10 seconds via AJAX
- **Intelligent caching** with Redis to reduce API load while maintaining freshness
- **WebSocket ready** infrastructure for future WebSocket implementation
- **Slippage updates** with real-time market impact calculations

## 🎨 Design

The platform features a Nintendo-inspired design with:
- **Gradient backgrounds** with smooth color transitions
- **Brand colors** using Jupiter purple, Hyperliquid blue, Solana green
- **Retro aesthetics** with gaming-inspired UI elements
- **Responsive layout** working on desktop, tablet, and mobile devices
- **Color-coded slippage** with green/orange/red indicators for market impact

## 🧪 Testing

The platform includes comprehensive testing:
- **Unit tests** for slippage models with edge case validation
- **Integration tests** for bridge simulation and API interactions
- **Performance tests** for Monte Carlo simulation speed

  ---


  
- **Demo scripts** showing real-world usage examples

