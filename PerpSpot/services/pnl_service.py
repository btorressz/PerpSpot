"""
PnL Simulation Service for Crypto Arbitrage Platform

Provides position-level PnL simulation with:
- Long/short position calculations
- Entry/exit price modeling
- Funding cost integration
- Slippage and fee estimation
- Risk metrics calculation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PnLSimulationService:
    """Advanced PnL simulation with risk metrics and funding calculations"""
    
    def __init__(self):
        self.default_fees = {
            'jupiter_spot': 0.0005,  # 5 bps
            'hyperliquid_perp': 0.0002,  # 2 bps maker, 5 bps taker
            'funding_frequency': 8  # hours between funding payments
        }
    
    def simulate_pnl(
        self,
        token: str,
        entry_price: float,
        exit_price: float,
        position_size_usd: float,
        position_type: str = "long",  # "long" or "short"
        funding_rate: float = 0.0,
        duration_hours: float = 1.0,
        slippage_bps: float = 0.0,
        custom_fees: Optional[Dict] = None
    ) -> Dict:
        """
        Simulate position-level PnL with comprehensive cost analysis
        
        Args:
            token: Token symbol (SOL, ETH, BTC, etc.)
            entry_price: Entry execution price
            exit_price: Exit execution price  
            position_size_usd: Position size in USD notional
            position_type: "long" or "short"
            funding_rate: Hourly funding rate (as decimal)
            duration_hours: Position duration in hours
            slippage_bps: Total slippage in basis points
            custom_fees: Override default fee structure
            
        Returns:
            Dict with PnL breakdown and risk metrics
        """
        try:
            fees = custom_fees or self.default_fees
            
            # Calculate position quantities
            quantity = position_size_usd / entry_price
            
            # Calculate raw PnL based on position type
            if position_type.lower() == "long":
                raw_pnl = quantity * (exit_price - entry_price)
            else:  # short
                raw_pnl = quantity * (entry_price - exit_price)
            
            # Calculate costs
            slippage_cost = position_size_usd * (slippage_bps / 10000)
            
            # Entry and exit fees
            entry_fee = position_size_usd * fees['jupiter_spot']
            exit_fee = (quantity * exit_price) * fees['hyperliquid_perp']
            total_fees = entry_fee + exit_fee
            
            # Funding costs (for perpetual positions)
            funding_payments = int(duration_hours / fees['funding_frequency'])
            funding_cost = 0.0
            if funding_payments > 0:
                hourly_funding_cost = position_size_usd * funding_rate
                if position_type.lower() == "long":
                    funding_cost = hourly_funding_cost * funding_payments
                else:  # short positions receive funding when positive
                    funding_cost = -hourly_funding_cost * funding_payments
            
            # Net PnL calculation
            net_pnl = raw_pnl - slippage_cost - total_fees - funding_cost
            
            # Calculate returns
            roi_percent = (net_pnl / position_size_usd) * 100
            
            # Risk metrics
            risk_metrics = self._calculate_position_risk_metrics(
                entry_price, exit_price, position_size_usd, 
                duration_hours, funding_rate
            )
            
            return {
                'simulation_results': {
                    'token': token,
                    'position_type': position_type,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'position_size_usd': position_size_usd,
                    'quantity': quantity,
                    'duration_hours': duration_hours,
                    'raw_pnl': raw_pnl,
                    'net_pnl': net_pnl,
                    'roi_percent': roi_percent
                },
                'cost_breakdown': {
                    'slippage_cost': slippage_cost,
                    'entry_fee': entry_fee,
                    'exit_fee': exit_fee,
                    'total_fees': total_fees,
                    'funding_cost': funding_cost,
                    'total_costs': slippage_cost + total_fees + funding_cost
                },
                'risk_metrics': risk_metrics,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in PnL simulation: {str(e)}")
            return {'error': str(e)}
    
    def simulate_time_series_pnl(
        self,
        token: str,
        price_series: pd.Series,
        entry_time: datetime,
        position_size_usd: float,
        position_type: str = "long",
        funding_rates: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        Simulate PnL over time series data
        
        Args:
            token: Token symbol
            price_series: Time series of prices with datetime index
            entry_time: Position entry timestamp
            position_size_usd: Position size in USD
            position_type: "long" or "short"
            funding_rates: Time series of funding rates
            
        Returns:
            DataFrame with time series PnL data
        """
        try:
            # Filter data from entry time
            pnl_data = price_series[price_series.index >= entry_time].copy()
            entry_price = pnl_data.iloc[0]
            
            # Calculate unrealized PnL for each timestamp
            quantity = position_size_usd / entry_price
            
            if position_type.lower() == "long":
                unrealized_pnl = quantity * (pnl_data - entry_price)
            else:
                unrealized_pnl = quantity * (entry_price - pnl_data)
            
            # Calculate cumulative funding costs if provided
            cumulative_funding = pd.Series(0.0, index=pnl_data.index)
            if funding_rates is not None:
                funding_subset = funding_rates[funding_rates.index >= entry_time]
                if len(funding_subset) > 0:
                    hourly_costs = position_size_usd * funding_subset
                    if position_type.lower() == "short":
                        hourly_costs = -hourly_costs
                    cumulative_funding = hourly_costs.cumsum()
            
            # Create comprehensive DataFrame
            pnl_df = pd.DataFrame({
                'price': pnl_data,
                'unrealized_pnl': unrealized_pnl,
                'cumulative_funding': cumulative_funding,
                'net_pnl': unrealized_pnl - cumulative_funding,
                'roi_percent': ((unrealized_pnl - cumulative_funding) / position_size_usd) * 100
            })
            
            return pnl_df
            
        except Exception as e:
            logger.error(f"Error in time series PnL simulation: {str(e)}")
            return pd.DataFrame()
    
    def calculate_risk_metrics(self, pnl_series: pd.Series) -> Dict:
        """
        Calculate comprehensive risk metrics from PnL time series
        
        Args:
            pnl_series: Time series of PnL values
            
        Returns:
            Dict with risk metrics
        """
        try:
            if len(pnl_series) == 0:
                return {}
            
            # Basic statistics
            mean_pnl = pnl_series.mean()
            std_pnl = pnl_series.std()
            min_pnl = pnl_series.min()
            max_pnl = pnl_series.max()
            
            # Sharpe ratio (annualized, assuming hourly data)
            if std_pnl > 0:
                sharpe_ratio = (mean_pnl / std_pnl) * np.sqrt(24 * 365)
            else:
                sharpe_ratio = 0.0
            
            # Maximum drawdown
            cumulative = pnl_series.cumsum()
            running_max = cumulative.cummax()
            drawdown = cumulative - running_max
            max_drawdown = drawdown.min()
            
            # Value at Risk (5% and 1% levels)
            var_5pct = pnl_series.quantile(0.05)
            var_1pct = pnl_series.quantile(0.01)
            
            # Conditional Value at Risk (Expected Shortfall)
            cvar_5pct = pnl_series[pnl_series <= var_5pct].mean()
            
            # Win rate
            positive_returns = (pnl_series > 0).sum()
            win_rate = positive_returns / len(pnl_series)
            
            # Profit factor
            gross_profit = pnl_series[pnl_series > 0].sum()
            gross_loss = abs(pnl_series[pnl_series < 0].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            return {
                'mean_pnl': mean_pnl,
                'std_pnl': std_pnl,
                'min_pnl': min_pnl,
                'max_pnl': max_pnl,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'var_5pct': var_5pct,
                'var_1pct': var_1pct,
                'cvar_5pct': cvar_5pct,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_return': pnl_series.sum(),
                'volatility': std_pnl
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_position_risk_metrics(
        self,
        entry_price: float,
        exit_price: float,
        position_size_usd: float,
        duration_hours: float,
        funding_rate: float
    ) -> Dict:
        """Calculate risk metrics for individual position"""
        try:
            # Price volatility estimation (simplified)
            price_change_pct = abs(exit_price - entry_price) / entry_price
            
            # Estimated volatility (annualized)
            if duration_hours > 0:
                hourly_vol = price_change_pct / np.sqrt(duration_hours)
                annual_vol = hourly_vol * np.sqrt(24 * 365)
            else:
                annual_vol = 0.0
            
            # Position-specific metrics
            leverage_estimate = 1.0  # Assuming no leverage for spot positions
            position_risk = position_size_usd * annual_vol
            
            # Funding rate impact
            annual_funding_rate = funding_rate * 24 * 365
            funding_impact_pct = annual_funding_rate * 100
            
            return {
                'annual_volatility': annual_vol,
                'position_risk_usd': position_risk,
                'leverage': leverage_estimate,
                'funding_impact_percent': funding_impact_pct,
                'price_change_percent': price_change_pct * 100,
                'duration_hours': duration_hours
            }
            
        except Exception as e:
            logger.error(f"Error calculating position risk metrics: {str(e)}")
            return {}

# Global service instance
pnl_service = PnLSimulationService()