# Perp Spot - Crypto Arbitrage Platform

## Overview 

A sophisticated cryptocurrency perpetuals arbitrage trading platform called "Perp Spot Crypto Arbitrage" that bridges Jupiter spot trading with Hyperliquid perpetual futures. Features real-time WebSocket data feeds with mainnet/testnet fallback, arbitrage opportunity detection, interactive dashboard with Chart.js visualization, execution latency modeling, Monte Carlo simulation modeling, advanced slippage management with standardized color-coded visualization (Green ≤50bps, Orange 50-200bps, Red >200bps), comprehensive analytics including Z-score spread detection and VaR calculations, Redis-backed caching, trading simulation capabilities, and dynamic token discovery supporting 100+ cryptocurrency pairs.

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
