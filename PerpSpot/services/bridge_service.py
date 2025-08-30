"""
Cross-Protocol Arbitrage Bridge Service

This service provides sophisticated modeling and simulation of arbitrage opportunities
between Jupiter (Solana spot DEX) and Hyperliquid (perpetuals), including:

- Bridge execution latency modeling
- Cross-protocol fee calculations
- Funding rate impact during execution windows
- Risk-adjusted profit projections
- Execution template management
"""

import numpy as np
import pandas as pd
import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class BridgeLatency:
    """Models expected latency for cross-protocol operations"""
    solana_tx_time: float = 0.4  # seconds
    hyperliquid_tx_time: float = 0.2  # seconds
    network_propagation: float = 0.1  # seconds
    slippage_discovery: float = 0.3  # seconds
    total_expected: float = 1.0  # seconds total


@dataclass 
class ExecutionCosts:
    """Models all costs involved in bridge arbitrage"""
    solana_gas_fee: float = 0.0001  # SOL
    hyperliquid_fee_rate: float = 0.0003  # 3 bps
    bridge_fee: float = 0.0  # Theoretical bridge fee
    slippage_impact: float = 0.002  # 20 bps expected slippage


@dataclass
class ExecutionTemplate:
    """Reusable execution template for bridge arbitrage"""
    name: str
    token_pair: str
    trade_size: float
    max_latency: float
    min_spread_bps: float
    funding_threshold: float
    preferred_direction: str  # 'long_perp', 'short_perp', 'auto'
    risk_multiplier: float = 1.0
    created_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class BridgeArbitrageService:
    """
    Advanced service for modeling cross-protocol arbitrage opportunities
    with comprehensive risk and latency modeling
    """
    
    def __init__(self, arbitrage_service=None):
        self.arbitrage_service = arbitrage_service
        self.execution_templates: List[ExecutionTemplate] = []
        self.historical_simulations = []
        
        # Load default execution templates
        self._load_default_templates()
        
        # Bridge configuration
        self.bridge_config = {
            'max_bridge_latency': 5.0,  # seconds
            'funding_decay_rate': 0.1,  # per second
            'min_profitable_spread': 0.5,  # 50 bps minimum
            'risk_free_rate': 0.03,  # 3% annual
        }
        
        logger.info("Bridge Arbitrage Service initialized")
    
    def _load_default_templates(self):
        """Load default execution templates for popular pairs"""
        default_templates = [
            ExecutionTemplate(
                name="SOL Scalping",
                token_pair="SOL-USDC", 
                trade_size=1000.0,
                max_latency=2.0,
                min_spread_bps=30,
                funding_threshold=-0.01,
                preferred_direction="auto"
            ),
            ExecutionTemplate(
                name="ETH Conservative",
                token_pair="ETH-USDC",
                trade_size=2000.0, 
                max_latency=3.0,
                min_spread_bps=50,
                funding_threshold=-0.005,
                preferred_direction="long_perp"
            ),
            ExecutionTemplate(
                name="BTC Large Size",
                token_pair="BTC-USDC",
                trade_size=5000.0,
                max_latency=4.0, 
                min_spread_bps=40,
                funding_threshold=-0.008,
                preferred_direction="auto",
                risk_multiplier=0.8
            )
        ]
        self.execution_templates.extend(default_templates)
    
    def simulate_bridge_execution(
        self, 
        token: str, 
        size: float, 
        current_spread_bps: float,
        jupiter_price: float,
        hyperliquid_price: float,
        funding_rate: float = 0.0,
        template: Optional[ExecutionTemplate] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive bridge arbitrage simulation with latency modeling
        
        Returns detailed execution plan with risk metrics
        """
        try:
            # Use template if provided, otherwise create dynamic parameters
            if template:
                max_latency = template.max_latency
                min_spread = template.min_spread_bps
                risk_mult = template.risk_multiplier
            else:
                max_latency = self.bridge_config['max_bridge_latency'] 
                min_spread = self.bridge_config['min_profitable_spread']
                risk_mult = 1.0
            
            # Model execution latency with Monte Carlo simulation
            latency_samples = np.random.gamma(2, max_latency/2, 1000)
            expected_latency = float(np.mean(latency_samples))
            latency_95th = float(np.percentile(latency_samples, 95))
            
            # Calculate spread decay during execution
            spread_decay = self._model_spread_decay(
                current_spread_bps, expected_latency, jupiter_price, hyperliquid_price
            )
            
            # Model funding rate impact during execution window
            funding_impact = self._calculate_funding_impact(
                funding_rate, expected_latency, size
            )
            
            # Calculate execution costs
            costs = self._calculate_execution_costs(token, size, jupiter_price)
            
            # Risk-adjusted profit calculation
            gross_profit = (current_spread_bps - spread_decay) * size / 10000
            net_profit = gross_profit - costs['total_fees'] - funding_impact
            risk_adjusted_profit = net_profit * risk_mult
            
            # Generate execution playbook
            playbook = self._generate_execution_playbook(
                token, size, jupiter_price, hyperliquid_price, 
                current_spread_bps, expected_latency
            )
            
            # Determine execution viability
            is_viable = bool(
                risk_adjusted_profit > 0 and 
                current_spread_bps >= min_spread and
                expected_latency <= max_latency
            )
            
            simulation_result = {
                'token': str(token),
                'size': float(size),
                'current_spread_bps': float(current_spread_bps),
                'jupiter_price': float(jupiter_price),
                'hyperliquid_price': float(hyperliquid_price),
                'execution_analysis': {
                    'expected_latency': float(expected_latency),
                    'latency_95th_percentile': float(latency_95th),
                    'spread_decay_bps': float(spread_decay),
                    'funding_impact_usd': float(funding_impact),
                    'gross_profit_usd': float(gross_profit),
                    'net_profit_usd': float(net_profit),
                    'risk_adjusted_profit_usd': float(risk_adjusted_profit),
                    'is_viable': bool(is_viable),
                    'profit_margin_percent': float((risk_adjusted_profit / size) * 100 if size > 0 else 0)
                },
                'costs_breakdown': costs,
                'risk_metrics': self._calculate_risk_metrics(
                    size, risk_adjusted_profit, latency_samples, funding_rate
                ),
                'execution_playbook': playbook,
                'timestamp': int(time.time() * 1000),
                'template_used': template.name if template else None
            }
            
            # Store simulation for historical analysis
            self.historical_simulations.append(simulation_result)
            
            # Keep only last 100 simulations in memory
            if len(self.historical_simulations) > 100:
                self.historical_simulations = self.historical_simulations[-100:]
            
            return simulation_result
            
        except Exception as e:
            logger.error(f"Error in bridge simulation for {token}: {str(e)}")
            return {
                'error': str(e),
                'token': str(token),
                'size': float(size),
                'is_viable': bool(False)
            }
    
    def simulate_bridge_execution_monte_carlo(
        self, 
        token: str, 
        notional_usd: float,
        template: Optional[str] = None,
        n_sims: int = 1000,
        jupiter_price: Optional[float] = None,
        hyperliquid_price: Optional[float] = None,
        funding_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Monte Carlo simulation for bridge execution with comprehensive modeling.
        
        This function implements sophisticated Monte Carlo sampling for:
        - Slippage variability across different market conditions
        - Execution delays with network and blockchain congestion modeling
        - Funding rate impact during execution windows
        - Cross-exchange fill skew and timing mismatches
        
        Args:
            token: Token symbol (e.g., 'SOL', 'ETH', 'BTC')
            notional_usd: Notional USD trade size
            template: Execution template name (optional)
            n_sims: Number of Monte Carlo simulations (default 1000, max 5000 for UI responsiveness)
            jupiter_price: Override Jupiter spot price (optional, will fetch if None)
            hyperliquid_price: Override Hyperliquid perp price (optional, will fetch if None)
            funding_rate: Override funding rate (optional, will fetch if None)
            
        Returns:
            Dict containing comprehensive simulation statistics:
            - mean_pnl, median_pnl: Central tendency measures
            - pnl_95pctile, pnl_5pctile: Risk percentiles
            - success_probability: Fraction of profitable simulations
            - avg_exec_ms, p99_exec_ms: Execution timing statistics
            - sample_draws: Small sample of individual simulation results
            
        Note:
            Uses float arithmetic for performance. For production accounting,
            consider using decimal.Decimal for final calculations.
        """
        try:
            # Limit simulations for UI responsiveness
            n_sims = min(n_sims, 5000)
            
            # Get current market data if not provided
            if any(x is None for x in [jupiter_price, hyperliquid_price, funding_rate]):
                if self.arbitrage_service:
                    price_data = self.arbitrage_service.get_price_data(token)
                    if price_data:
                        jupiter_data = price_data.get('jupiter', {})
                        hyperliquid_data = price_data.get('hyperliquid', {})
                        fallback_data = price_data.get('fallback', {})
                        
                        jupiter_price = jupiter_price or jupiter_data.get('spot', fallback_data.get('price', 100.0))
                        hyperliquid_price = hyperliquid_price or hyperliquid_data.get('mark', fallback_data.get('price', 101.0))
                        funding_rate = funding_rate or hyperliquid_data.get('funding_rate', 0.0)
                    else:
                        # Use demo prices for simulation
                        jupiter_price = jupiter_price or 100.0
                        hyperliquid_price = hyperliquid_price or 101.0
                        funding_rate = funding_rate or 0.0001
            
            # Get execution template if specified
            template_config = None
            if template:
                template_config = self.get_execution_template(template)
                
            # Calculate base spread
            spread_bps = abs(jupiter_price - hyperliquid_price) / jupiter_price * 10000
            
            # Monte Carlo simulation arrays
            pnl_samples = np.zeros(n_sims)
            exec_time_samples = np.zeros(n_sims)
            success_samples = np.zeros(n_sims, dtype=bool)
            
            # Simulation parameters with realistic distributions
            base_latency = 1.5  # Base execution time in seconds
            latency_std = 0.8   # Standard deviation for latency
            
            # Slippage parameters
            base_slippage_bps = 5.0  # Base slippage in basis points
            slippage_std = 3.0       # Slippage variability
            
            # Market impact based on trade size
            size_impact_factor = np.log(notional_usd / 1000) * 0.5  # Logarithmic size impact
            
            logger.info(f"Starting Monte Carlo simulation: {n_sims} runs for {token}, size: ${notional_usd}")
            
            for i in range(n_sims):
                # 1. Sample execution latency (exponential distribution with minimum)
                exec_latency = np.maximum(
                    np.random.exponential(base_latency),
                    0.2  # Minimum 200ms execution time
                )
                exec_time_samples[i] = exec_latency * 1000  # Convert to milliseconds
                
                # 2. Sample slippage variability (normal distribution, clipped)
                slippage_bps = np.maximum(
                    np.random.normal(base_slippage_bps + size_impact_factor, slippage_std),
                    0.1  # Minimum slippage
                )
                
                # 3. Model spread decay during execution
                decay_rate = 0.4 * (1 + np.random.normal(0, 0.2))  # Variable decay rate
                spread_decay = spread_bps * (1 - np.exp(-decay_rate * exec_latency))
                effective_spread = max(spread_bps - spread_decay, 0.1)
                
                # 4. Cross-exchange fill skew (timing mismatch risk)
                fill_skew_risk = np.random.exponential(0.3)  # Additional execution risk
                
                # 5. Funding rate impact during execution window
                funding_impact_bps = abs(funding_rate) * (exec_latency / 3600) * 8 * 10000  # Convert to bps
                
                # 6. Calculate gross PnL
                gross_pnl_bps = effective_spread - slippage_bps - funding_impact_bps - fill_skew_risk
                gross_pnl_usd = (gross_pnl_bps / 10000) * notional_usd
                
                # 7. Apply execution costs
                costs = self._calculate_execution_costs(token, notional_usd, jupiter_price)
                net_pnl = gross_pnl_usd - costs['total_fees']
                
                # 8. Apply template-specific risk adjustments
                if template_config:
                    risk_multiplier = getattr(template_config, 'risk_multiplier', 1.0)
                    net_pnl *= risk_multiplier
                
                # Store results
                pnl_samples[i] = net_pnl
                success_samples[i] = net_pnl > 0
            
            # Calculate comprehensive statistics
            mean_pnl = float(np.mean(pnl_samples))
            median_pnl = float(np.median(pnl_samples))
            pnl_95pctile = float(np.percentile(pnl_samples, 95))
            pnl_5pctile = float(np.percentile(pnl_samples, 5))
            success_probability = float(np.mean(success_samples))
            
            avg_exec_ms = float(np.mean(exec_time_samples))
            p99_exec_ms = float(np.percentile(exec_time_samples, 99))
            
            # Sample a few individual draws for inspection
            sample_indices = np.random.choice(n_sims, min(10, n_sims), replace=False)
            sample_draws = [
                {
                    'pnl_usd': float(pnl_samples[i]),
                    'exec_time_ms': float(exec_time_samples[i]),
                    'success': bool(success_samples[i])
                }
                for i in sample_indices
            ]
            
            # Risk metrics
            sharpe_ratio = mean_pnl / (np.std(pnl_samples) + 1e-6) if np.std(pnl_samples) > 0 else 0
            max_loss = float(np.min(pnl_samples))
            
            logger.info(f"Monte Carlo completed: mean PnL ${mean_pnl:.2f}, success rate {success_probability:.1%}")
            
            return {
                'simulation_stats': {
                    'n_simulations': n_sims,
                    'mean_pnl': mean_pnl,
                    'median_pnl': median_pnl,
                    'pnl_95pctile': pnl_95pctile,
                    'pnl_5pctile': pnl_5pctile,
                    'success_probability': success_probability,
                    'avg_exec_ms': avg_exec_ms,
                    'p99_exec_ms': p99_exec_ms,
                    'sharpe_ratio': float(sharpe_ratio),
                    'max_loss': max_loss,
                    'sample_draws': sample_draws
                },
                'input_parameters': {
                    'token': token,
                    'notional_usd': notional_usd,
                    'jupiter_price': jupiter_price,
                    'hyperliquid_price': hyperliquid_price,
                    'funding_rate': funding_rate,
                    'spread_bps': spread_bps,
                    'template': template
                },
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation for {token}: {str(e)}")
            return {
                'error': str(e),
                'token': token,
                'notional_usd': notional_usd,
                'n_sims': n_sims
            }
    
    def _model_spread_decay(
        self, 
        initial_spread_bps: float, 
        latency: float,
        jupiter_price: float, 
        hyperliquid_price: float
    ) -> float:
        """Model how spreads decay during execution latency"""
        # Exponential decay model based on market efficiency
        decay_rate = 0.3  # spreads decay 30% per second on average
        volatility_factor = abs(jupiter_price - hyperliquid_price) / jupiter_price
        
        # Higher volatility = faster spread decay
        adjusted_decay = decay_rate * (1 + volatility_factor * 2)
        
        spread_decay = initial_spread_bps * (1 - np.exp(-adjusted_decay * latency))
        return min(spread_decay, initial_spread_bps * 0.8)  # Cap at 80% decay
    
    def _calculate_funding_impact(
        self, 
        funding_rate: float, 
        latency: float, 
        position_size: float
    ) -> float:
        """Calculate funding rate impact during execution window"""
        if funding_rate == 0:
            return 0.0
        
        # Funding rates are typically 8-hour rates, convert to per-second
        hourly_rate = funding_rate / 8
        funding_impact = hourly_rate * (latency / 3600) * position_size
        return abs(funding_impact)  # Always a cost
    
    def _calculate_execution_costs(
        self, 
        token: str, 
        size: float, 
        price: float
    ) -> Dict[str, float]:
        """Calculate comprehensive execution costs"""
        costs = ExecutionCosts()
        
        # Solana transaction fees (in USD)
        sol_price = 180.0  # Approximate SOL price for fee calculation
        gas_fee_usd = costs.solana_gas_fee * sol_price
        
        # Hyperliquid trading fees
        hyperliquid_fee_usd = size * costs.hyperliquid_fee_rate
        
        # Slippage impact
        slippage_usd = size * costs.slippage_impact
        
        total_fees = gas_fee_usd + hyperliquid_fee_usd + slippage_usd + costs.bridge_fee
        
        return {
            'gas_fee_usd': gas_fee_usd,
            'trading_fee_usd': hyperliquid_fee_usd, 
            'slippage_usd': slippage_usd,
            'bridge_fee_usd': costs.bridge_fee,
            'total_fees': total_fees
        }
    
    def _calculate_risk_metrics(
        self, 
        size: float, 
        expected_profit: float, 
        latency_samples: np.ndarray,
        funding_rate: float
    ) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        # Value at Risk (95th percentile loss)
        profit_samples = []
        for latency in latency_samples[:100]:  # Sample subset for speed
            simulated_profit = expected_profit * np.random.normal(1.0, 0.1)
            profit_samples.append(simulated_profit)
        
        profit_samples = np.array(profit_samples)
        var_95 = np.percentile(profit_samples, 5)  # 5th percentile = 95% VaR
        
        return {
            'value_at_risk_95': float(abs(var_95)),
            'sharpe_ratio': float(expected_profit / (np.std(profit_samples) + 1e-6)),
            'max_drawdown': float(abs(min(profit_samples))) if len(profit_samples) > 0 else 0.0,
            'success_probability': float(np.mean(profit_samples > 0)),
            'funding_risk_factor': float(abs(funding_rate) * 10),  # Scale for visibility
            'latency_risk_score': float(np.std(latency_samples) / np.mean(latency_samples))
        }
    
    def _generate_execution_playbook(
        self, 
        token: str, 
        size: float, 
        jupiter_price: float,
        hyperliquid_price: float, 
        spread_bps: float, 
        expected_latency: float
    ) -> Dict[str, Any]:
        """Generate detailed execution playbook"""
        
        # Determine optimal execution order based on prices
        if jupiter_price < hyperliquid_price:
            # Buy on Jupiter (spot), sell on Hyperliquid (perp)
            strategy = "long_spot_short_perp"
            entry_exchange = "Jupiter"
            exit_exchange = "Hyperliquid"
            direction = "Buy low on spot, short high on perps"
        else:
            # Sell on Jupiter (spot), buy on Hyperliquid (perp)  
            strategy = "short_spot_long_perp"
            entry_exchange = "Hyperliquid"
            exit_exchange = "Jupiter"
            direction = "Long low perps, sell high spot"
        
        return {
            'strategy_type': strategy,
            'execution_steps': [
                {
                    'step': 1,
                    'action': f"Execute {direction.split(',')[0].strip()}",
                    'exchange': entry_exchange,
                    'estimated_time': expected_latency * 0.6,
                    'size': size,
                    'price': jupiter_price if 'spot' in strategy.split('_')[1] else hyperliquid_price
                },
                {
                    'step': 2,
                    'action': f"Execute {direction.split(',')[1].strip()}",
                    'exchange': exit_exchange,
                    'estimated_time': expected_latency * 0.4,
                    'size': size,
                    'price': hyperliquid_price if exit_exchange == 'Hyperliquid' else jupiter_price
                }
            ],
            'risk_controls': {
                'max_slippage': "2%",
                'position_timeout': f"{expected_latency * 2:.1f}s",
                'stop_loss': f"{spread_bps * 0.3:.1f} bps"
            },
            'expected_timeline': {
                'total_execution': f"{expected_latency:.2f}s",
                'profit_realization': f"{expected_latency + 1:.2f}s"
            }
        }
    
    def get_bridge_analytics(self, time_window_hours: int = 24, token: str = None) -> Dict[str, Any]:
        """Generate comprehensive bridge analytics"""
        try:
            cutoff_time = time.time() - (time_window_hours * 3600)
            recent_sims = [
                sim for sim in self.historical_simulations 
                if sim.get('timestamp', 0) / 1000 > cutoff_time
            ]
            
            # Filter by token if specified
            if token:
                recent_sims = [
                    sim for sim in recent_sims
                    if sim.get('token', '').upper() == token.upper()
                ]
            
            if not recent_sims:
                return {
                    'total_simulations': 0,
                    'viable_opportunities': 0,
                    'analytics': None
                }
            
            # Convert to pandas for analysis
            df = pd.DataFrame([
                {
                    'timestamp': sim['timestamp'],
                    'token': sim['token'], 
                    'size': sim['size'],
                    'spread_bps': sim['current_spread_bps'],
                    'profit_usd': sim['execution_analysis']['risk_adjusted_profit_usd'],
                    'latency': sim['execution_analysis']['expected_latency'],
                    'is_viable': bool(sim['execution_analysis']['is_viable'])
                }
                for sim in recent_sims
            ])
            
            viable_df = df[df['is_viable'] == True]
            
            analytics = {
                'volume_analytics': {
                    'total_volume': float(df['size'].sum()),
                    'viable_volume': float(viable_df['size'].sum()) if not viable_df.empty else 0.0,
                    'avg_trade_size': float(df['size'].mean()),
                    'volume_by_token': {k: float(v) for k, v in df.groupby('token')['size'].sum().to_dict().items()}
                },
                'profitability_metrics': {
                    'total_potential_profit': float(viable_df['profit_usd'].sum()) if not viable_df.empty else 0.0,
                    'avg_profit_per_trade': float(viable_df['profit_usd'].mean()) if not viable_df.empty else 0.0,
                    'profit_by_token': {k: float(v) for k, v in viable_df.groupby('token')['profit_usd'].sum().to_dict().items()} if not viable_df.empty else {},
                    'success_rate': float((len(viable_df) / len(df)) * 100) if not df.empty else 0.0
                },
                'latency_analysis': {
                    'avg_execution_time': float(df['latency'].mean()),
                    'p95_execution_time': float(df['latency'].quantile(0.95)),
                    'fastest_execution': float(df['latency'].min()),
                    'slowest_execution': float(df['latency'].max())
                },
                'spread_analysis': {
                    'avg_spread_bps': float(df['spread_bps'].mean()),
                    'max_spread_bps': float(df['spread_bps'].max()),
                    'viable_spread_threshold': float(viable_df['spread_bps'].min()) if not viable_df.empty else 0.0
                }
            }
            
            return {
                'total_simulations': len(recent_sims),
                'viable_opportunities': len(viable_df),
                'time_window_hours': time_window_hours,
                'analytics': analytics,
                'generated_at': int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error generating bridge analytics: {str(e)}")
            return {'error': str(e)}
    
    def save_execution_template(self, template_data: Dict[str, Any]) -> bool:
        """Save a new execution template"""
        try:
            template = ExecutionTemplate(**template_data)
            self.execution_templates.append(template)
            logger.info(f"Saved execution template: {template.name}")
            return True
        except Exception as e:
            logger.error(f"Error saving template: {str(e)}")
            return False
    
    def get_execution_templates(self) -> List[Dict[str, Any]]:
        """Get all execution templates"""
        return [asdict(template) for template in self.execution_templates]
    
    def delete_execution_template(self, template_name: str) -> bool:
        """Delete an execution template by name"""
        try:
            self.execution_templates = [
                t for t in self.execution_templates 
                if t.name != template_name
            ]
            logger.info(f"Deleted execution template: {template_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting template: {str(e)}")
            return False
    
    def get_historical_spread_bridges(self, token: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical analysis of spread bridges and their duration"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            recent_sims = [
                sim for sim in self.historical_simulations 
                if sim.get('timestamp', 0) / 1000 > cutoff_time
            ]
            
            if token:
                recent_sims = [sim for sim in recent_sims if sim.get('token') == token]
            
            # Group by time windows to identify spread bridges
            spread_bridges = []
            current_bridge = None
            
            for sim in sorted(recent_sims, key=lambda x: x.get('timestamp', 0)):
                if sim['execution_analysis']['is_viable']:
                    if current_bridge is None:
                        # Start new bridge
                        current_bridge = {
                            'start_time': sim['timestamp'],
                            'end_time': sim['timestamp'],
                            'token': sim['token'],
                            'max_spread_bps': sim['current_spread_bps'],
                            'min_spread_bps': sim['current_spread_bps'],
                            'total_opportunities': 1,
                            'total_potential_profit': sim['execution_analysis']['risk_adjusted_profit_usd'],
                            'avg_latency': sim['execution_analysis']['expected_latency']
                        }
                    else:
                        # Extend current bridge
                        current_bridge['end_time'] = sim['timestamp'] 
                        current_bridge['max_spread_bps'] = max(
                            current_bridge['max_spread_bps'], 
                            sim['current_spread_bps']
                        )
                        current_bridge['min_spread_bps'] = min(
                            current_bridge['min_spread_bps'],
                            sim['current_spread_bps'] 
                        )
                        current_bridge['total_opportunities'] += 1
                        current_bridge['total_potential_profit'] += sim['execution_analysis']['risk_adjusted_profit_usd']
                        current_bridge['avg_latency'] = (
                            current_bridge['avg_latency'] + sim['execution_analysis']['expected_latency']
                        ) / 2
                else:
                    # End current bridge if exists
                    if current_bridge is not None:
                        current_bridge['duration_seconds'] = (
                            current_bridge['end_time'] - current_bridge['start_time']
                        ) / 1000
                        current_bridge['avg_potential_profit'] = (
                            current_bridge['total_potential_profit'] / 
                            current_bridge['total_opportunities']
                        )
                        spread_bridges.append(current_bridge)
                        current_bridge = None
            
            # Close final bridge if exists
            if current_bridge is not None:
                current_bridge['duration_seconds'] = (
                    current_bridge['end_time'] - current_bridge['start_time']
                ) / 1000
                current_bridge['avg_potential_profit'] = (
                    current_bridge['total_potential_profit'] / 
                    current_bridge['total_opportunities']
                )
                spread_bridges.append(current_bridge)
            
            return spread_bridges
            
        except Exception as e:
            logger.error(f"Error analyzing spread bridges: {str(e)}")
            return []


# Initialize global bridge service instance
bridge_service = BridgeArbitrageService()