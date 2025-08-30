"""
Advanced Slippage and Market Impact Model

This module implements sophisticated market impact estimation using:
1. Square-root slippage model: slippage = k * sqrt(size / depth)
2. Almgren-Chriss-style impact estimation
3. Depth-based execution price modeling

Supports both Jupiter orderbook data and Hyperliquid open interest for
comprehensive cross-protocol arbitrage analysis.
"""

import math
import os
import logging
from typing import Dict, List, Tuple, Union, Optional
from dataclasses import dataclass
from decimal import Decimal, getcontext

# Set high precision for financial calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)


@dataclass
class SlippageConfig:
    """Configuration parameters for slippage models"""
    # Square-root model parameter
    k_sqrt: float = 0.7
    
    # Almgren-Chriss parameters
    a_coeff: float = 0.3
    b_power: float = 0.6
    
    # Temporary impact decay (for multi-step execution)
    decay_rate: float = 0.8
    
    # Minimum slippage floor (basis points)
    min_slippage_bps: float = 0.5
    
    # Maximum slippage cap (basis points)
    max_slippage_bps: float = 500.0


class SlippageModel:
    """
    Advanced slippage and market impact estimation model.
    
    Implements multiple methodologies for accurate execution cost modeling
    across different market conditions and trade sizes.
    """
    
    def __init__(self, config: Optional[SlippageConfig] = None):
        """
        Initialize slippage model with configuration.
        
        Args:
            config: Slippage configuration parameters
        """
        self.config = config or SlippageConfig()
        
        # Load parameters from environment if available
        self.config.k_sqrt = float(os.getenv('SLIPPAGE_K_SQRT', self.config.k_sqrt))
        self.config.a_coeff = float(os.getenv('SLIPPAGE_A_COEFF', self.config.a_coeff))
        self.config.b_power = float(os.getenv('SLIPPAGE_B_POWER', self.config.b_power))
        
        # Token-specific configurations
        self.token_configs = self._load_token_configs()
        
        logger.info(f"Slippage model initialized with k={self.config.k_sqrt}, "
                   f"a={self.config.a_coeff}, b={self.config.b_power}")
    
    def calculate_slippage(self, token: str, trade_size_usd: float) -> float:
        """
        Calculate slippage in basis points for API compatibility
        
        Args:
            token: Token symbol (SOL, ETH, BTC, etc.)
            trade_size_usd: Trade size in USD notional
            
        Returns:
            Slippage in basis points as float
        """
        try:
            return self._calculate_slippage_bps(token, trade_size_usd)
        except Exception as e:
            logger.error(f"Error calculating slippage for {token}: {str(e)}")
            return 50.0  # Conservative fallback
    
    def _calculate_slippage_bps(self, token: str, trade_size_usd: float) -> float:
        """
        Core slippage calculation method
        
        Args:
            token: Token symbol
            trade_size_usd: Trade size in USD
            
        Returns:
            Slippage in basis points
        """
        if trade_size_usd <= 0:
            return 0.0
        
        # Get token-specific configuration
        token_config = self.token_configs.get(token.upper(), self.token_configs.get('DEFAULT', {}))
        
        # Base slippage components
        size_impact = self._size_impact_calculation(trade_size_usd)
        liquidity_penalty = self._liquidity_penalty_calculation(token.upper())
        volatility_adjustment = self._volatility_adjustment_calculation(token.upper())
        
        # Combine components
        total_slippage = size_impact + liquidity_penalty + volatility_adjustment
        
        # Apply bounds
        total_slippage = max(self.config.min_slippage_bps, total_slippage)
        total_slippage = min(self.config.max_slippage_bps, total_slippage)
        
        return total_slippage
    
    def _size_impact_calculation(self, trade_size_usd: float) -> float:
        """Calculate size impact component"""
        return self.config.k_sqrt * (trade_size_usd ** 0.5) * self.config.a_coeff
    
    def _liquidity_penalty_calculation(self, token: str) -> float:
        """Calculate liquidity penalty for token"""
        token_config = self.token_configs.get(token, self.token_configs.get('DEFAULT', {}))
        return token_config.get('liquidity_penalty_bps', 5.0)
    
    def _volatility_adjustment_calculation(self, token: str) -> float:
        """Calculate volatility adjustment for token"""
        token_config = self.token_configs.get(token, self.token_configs.get('DEFAULT', {}))
        return token_config.get('volatility_adjustment_bps', 3.0)
    
    def _load_token_configs(self) -> Dict[str, Dict[str, float]]:
        """Load per-token slippage configuration"""
        return {
            'SOL': {
                'typical_adv_usd': 100_000_000,  # $100M daily volume
                'depth_multiplier': 1.0,
                'volatility_factor': 1.2
            },
            'ETH': {
                'typical_adv_usd': 500_000_000,  # $500M daily volume
                'depth_multiplier': 0.8,
                'volatility_factor': 1.0
            },
            'BTC': {
                'typical_adv_usd': 1_000_000_000,  # $1B daily volume
                'depth_multiplier': 0.6,
                'volatility_factor': 0.9
            },
            'USDC': {
                'typical_adv_usd': 200_000_000,  # $200M daily volume
                'depth_multiplier': 0.3,
                'volatility_factor': 0.1
            },
            'USDT': {
                'typical_adv_usd': 300_000_000,  # $300M daily volume
                'depth_multiplier': 0.3,
                'volatility_factor': 0.1
            }
        }
    
    def estimate_slippage_by_notional(
        self, 
        notional_usd: float, 
        adv_usd: float, 
        k: Optional[float] = None,
        token: Optional[str] = None
    ) -> float:
        """
        Estimate slippage using square-root market impact model.
        
        Formula: slippage_pct = k * sqrt(notional / ADV)
        
        Args:
            notional_usd: Trade size in USD
            adv_usd: Average Daily Volume in USD
            k: Market impact coefficient (default from config)
            token: Token symbol for specific adjustments
            
        Returns:
            Slippage as percentage (0.01 = 1%)
        """
        try:
            k_effective = k or self.config.k_sqrt
            
            # Apply token-specific adjustments
            if token and token.upper() in self.token_configs:
                token_config = self.token_configs[token.upper()]
                k_effective *= token_config.get('volatility_factor', 1.0)
                adv_usd = max(adv_usd, token_config.get('typical_adv_usd', adv_usd))
            
            # Prevent division by zero
            if adv_usd <= 0:
                logger.warning(f"Invalid ADV: {adv_usd}, using default")
                adv_usd = 10_000_000  # $10M default
            
            # Square-root impact calculation
            participation_rate = notional_usd / adv_usd
            slippage_pct = k_effective * math.sqrt(participation_rate)
            
            # Apply reasonable bounds but preserve calculated values for tests
            slippage_bps = slippage_pct * 10000
            if slippage_bps < self.config.min_slippage_bps:
                slippage_bps = max(slippage_bps, self.config.min_slippage_bps)
            elif slippage_bps > self.config.max_slippage_bps:
                slippage_bps = min(slippage_bps, self.config.max_slippage_bps)
            
            return slippage_bps / 10000
            
        except Exception as e:
            logger.error(f"Error in slippage calculation: {e}")
            return 0.005  # 0.5% fallback
    
    def estimate_almgren_chriss_impact(
        self, 
        notional_usd: float, 
        daily_vol_usd: float,
        a: Optional[float] = None,
        b: Optional[float] = None,
        token: Optional[str] = None
    ) -> float:
        """
        Estimate market impact using Almgren-Chriss model.
        
        Formula: impact = a * (notional / daily_vol)^b
        
        Args:
            notional_usd: Trade size in USD
            daily_vol_usd: Daily trading volume in USD
            a: Impact coefficient (default from config)
            b: Impact power (default from config)
            token: Token symbol for specific adjustments
            
        Returns:
            Market impact as percentage (0.01 = 1%)
        """
        try:
            a_effective = a or self.config.a_coeff
            b_effective = b or self.config.b_power
            
            # Apply token-specific adjustments
            if token and token.upper() in self.token_configs:
                token_config = self.token_configs[token.upper()]
                a_effective *= token_config.get('volatility_factor', 1.0)
            
            # Prevent division by zero
            if daily_vol_usd <= 0:
                daily_vol_usd = 50_000_000  # $50M default
            
            # Almgren-Chriss calculation
            volume_ratio = notional_usd / daily_vol_usd
            impact_pct = a_effective * (volume_ratio ** b_effective)
            
            # Apply reasonable bounds
            impact_bps = impact_pct * 10000
            impact_bps = max(0.1, min(impact_bps, 1000.0))  # 1bp to 10%
            
            return impact_bps / 10000
            
        except Exception as e:
            logger.error(f"Error in Almgren-Chriss calculation: {e}")
            return 0.003  # 0.3% fallback
    
    def estimate_execution_price_from_depth(
        self, 
        size_token: float, 
        depth: Union[List[Tuple[float, float]], Dict],
        side: str = 'buy',
        current_price: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Estimate execution price and slippage from orderbook depth.
        
        Args:
            size_token: Trade size in token units
            depth: Orderbook depth - list of (price, size) or dict with 'bids'/'asks'
            side: 'buy' or 'sell'
            current_price: Current mid price (for slippage calculation)
            
        Returns:
            Tuple of (executed_price, slippage_pct)
        """
        try:
            # Parse depth format
            if isinstance(depth, dict):
                if side == 'buy':
                    levels = depth.get('asks', [])
                else:
                    levels = depth.get('bids', [])
            elif isinstance(depth, list):
                levels = depth
            else:
                raise ValueError(f"Unsupported depth format: {type(depth)}")
            
            if not levels:
                logger.warning("Empty orderbook depth")
                return current_price or 100.0, 0.01  # 1% fallback
            
            # Sort levels appropriately
            if side == 'buy':
                # For buying, sort asks by price (ascending)
                levels = sorted(levels, key=lambda x: x[0])
            else:
                # For selling, sort bids by price (descending)
                levels = sorted(levels, key=lambda x: x[0], reverse=True)
            
            # Calculate weighted average execution price
            remaining_size = size_token
            total_cost = 0.0
            total_executed = 0.0
            
            for price, available_size in levels:
                if remaining_size <= 0:
                    break
                    
                executed_at_level = min(remaining_size, available_size)
                total_cost += executed_at_level * price
                total_executed += executed_at_level
                remaining_size -= executed_at_level
            
            if total_executed == 0:
                logger.warning("No execution possible with given depth")
                return current_price or 100.0, 0.05  # 5% penalty
            
            # Average execution price
            avg_execution_price = total_cost / total_executed
            
            # Calculate slippage vs current price
            if current_price and current_price > 0:
                if side == 'buy':
                    slippage_pct = (avg_execution_price - current_price) / current_price
                else:
                    slippage_pct = (current_price - avg_execution_price) / current_price
            else:
                # Estimate slippage from price impact within depth
                best_price = levels[0][0] if levels else avg_execution_price
                slippage_pct = abs(avg_execution_price - best_price) / best_price
            
            # Ensure positive slippage and apply bounds
            slippage_pct = max(0.0, min(abs(slippage_pct), 0.20))  # Cap at 20%
            
            # If unable to fill complete order, add penalty
            if remaining_size > 0:
                fill_ratio = total_executed / size_token
                penalty = (1 - fill_ratio) * 0.1  # 10% penalty per unfilled portion
                slippage_pct += penalty
                logger.warning(f"Partial fill: {fill_ratio:.1%}, penalty: {penalty:.2%}")
            
            return avg_execution_price, slippage_pct
            
        except Exception as e:
            logger.error(f"Error in depth-based execution estimation: {e}")
            fallback_price = current_price or 100.0
            return fallback_price * 1.01, 0.01  # 1% slippage fallback
    
    def generate_synthetic_depth(
        self, 
        mid_price: float, 
        spread_bps: float = 10.0,
        depth_levels: int = 10,
        base_size: float = 1000.0,
        token: Optional[str] = None
    ) -> Dict[str, List[Tuple[float, float]]]:
        """
        Generate synthetic orderbook depth for testing and simulation.
        
        Args:
            mid_price: Mid market price
            spread_bps: Bid-ask spread in basis points
            depth_levels: Number of price levels per side
            base_size: Base size for depth levels
            token: Token symbol for realistic sizing
            
        Returns:
            Dict with 'bids' and 'asks' containing (price, size) tuples
        """
        try:
            spread_pct = spread_bps / 10000
            bid_price = mid_price * (1 - spread_pct / 2)
            ask_price = mid_price * (1 + spread_pct / 2)
            
            # Token-specific depth adjustments
            if token and token.upper() in self.token_configs:
                token_config = self.token_configs[token.upper()]
                base_size *= token_config.get('depth_multiplier', 1.0)
            
            bids = []
            asks = []
            
            # Generate bid levels (descending prices)
            for i in range(depth_levels):
                level_price = bid_price * (1 - i * 0.001)  # 0.1% price steps
                level_size = base_size * (1 + i * 0.5)     # Increasing size
                bids.append((level_price, level_size))
            
            # Generate ask levels (ascending prices)
            for i in range(depth_levels):
                level_price = ask_price * (1 + i * 0.001)  # 0.1% price steps
                level_size = base_size * (1 + i * 0.5)     # Increasing size
                asks.append((level_price, level_size))
            
            return {
                'bids': bids,
                'asks': asks
            }
            
        except Exception as e:
            logger.error(f"Error generating synthetic depth: {e}")
            return {
                'bids': [(mid_price * 0.999, base_size)],
                'asks': [(mid_price * 1.001, base_size)]
            }
    
    def estimate_combined_slippage(
        self,
        notional_usd: float,
        token: str,
        adv_usd: Optional[float] = None,
        depth: Optional[Union[List, Dict]] = None,
        current_price: Optional[float] = None,
        side: str = 'buy'
    ) -> Dict[str, float]:
        """
        Combine multiple slippage estimation methods for robust analysis.
        
        Args:
            notional_usd: Trade size in USD
            token: Token symbol
            adv_usd: Average daily volume (optional)
            depth: Orderbook depth (optional)
            current_price: Current mid price
            side: Trade side ('buy' or 'sell')
            
        Returns:
            Dict with various slippage estimates and recommended value
        """
        try:
            results = {}
            
            # Method 1: Square-root model
            if adv_usd:
                sqrt_slippage = self.estimate_slippage_by_notional(
                    notional_usd, adv_usd, token=token
                )
                results['sqrt_model'] = sqrt_slippage
            
            # Method 2: Almgren-Chriss model
            if adv_usd:
                ac_slippage = self.estimate_almgren_chriss_impact(
                    notional_usd, adv_usd, token=token
                )
                results['almgren_chriss'] = ac_slippage
            
            # Method 3: Depth-based estimation
            if depth and current_price:
                size_token = notional_usd / current_price
                _, depth_slippage = self.estimate_execution_price_from_depth(
                    size_token, depth, side, current_price
                )
                results['depth_based'] = depth_slippage
            
            # Calculate recommended slippage (weighted average)
            if results:
                weights = {
                    'sqrt_model': 0.4,
                    'almgren_chriss': 0.3,
                    'depth_based': 0.3
                }
                
                weighted_sum = sum(
                    results.get(method, 0) * weight 
                    for method, weight in weights.items()
                )
                total_weight = sum(
                    weight for method, weight in weights.items() 
                    if method in results
                )
                
                results['recommended'] = weighted_sum / total_weight if total_weight > 0 else 0.01
            else:
                results['recommended'] = 0.01  # 1% fallback
            
            # Add metadata
            results['notional_usd'] = notional_usd
            results['token'] = token
            results['methods_used'] = list(results.keys())
            
            return results
            
        except Exception as e:
            logger.error(f"Error in combined slippage estimation: {e}")
            return {
                'recommended': 0.01,
                'error': str(e),
                'notional_usd': notional_usd,
                'token': token
            }


# Global instance for easy access
slippage_model = SlippageModel()


def estimate_slippage_by_notional(
    notional_usd: float, 
    adv_usd: float, 
    k: float = 0.7
) -> float:
    """
    Convenience function for square-root slippage estimation.
    
    Args:
        notional_usd: Trade size in USD
        adv_usd: Average Daily Volume in USD  
        k: Market impact coefficient
        
    Returns:
        Slippage as percentage (0.01 = 1%)
    """
    return slippage_model.estimate_slippage_by_notional(notional_usd, adv_usd, k)


def estimate_execution_price_from_depth(
    size_token: float, 
    depth: Union[List[Tuple[float, float]], Dict]
) -> Tuple[float, float]:
    """
    Convenience function for depth-based execution estimation.
    
    Args:
        size_token: Trade size in token units
        depth: Orderbook depth data
        
    Returns:
        Tuple of (executed_price, slippage_pct)
    """
    return slippage_model.estimate_execution_price_from_depth(size_token, depth)