import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from app import db
from models import PriceData, FundingRate, ArbitrageOpportunity

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.min_spread_bps = 10  # Minimum spread in basis points to consider
        self.significant_spread_bps = 50  # Significant spread threshold
    
    def calculate_spread_bps(self, spot_price: float, perp_price: float) -> float:
        """Calculate spread in basis points between spot and perp prices"""
        if spot_price <= 0 or perp_price <= 0:
            return 0.0
        
        spread = (perp_price - spot_price) / spot_price
        spread_bps = spread * 10000  # Convert to basis points
        return spread_bps
    
    def calculate_slippage_impact(self, amount: float, order_book: Dict, side: str = 'buy') -> float:
        """Calculate slippage impact for a given trade size"""
        try:
            if not order_book or 'levels' not in order_book:
                return 0.0
            
            levels = order_book['levels']
            bids = levels[1] if len(levels) > 1 else []  # Bid levels
            asks = levels[0] if len(levels) > 0 else []  # Ask levels
            
            if side.lower() == 'buy':
                # For buy orders, we consume asks
                return self._calculate_market_impact(amount, asks, 'buy')
            else:
                # For sell orders, we consume bids
                return self._calculate_market_impact(amount, bids, 'sell')
                
        except Exception as e:
            logger.error(f"Error calculating slippage impact: {e}")
            return 0.0
    
    def _calculate_market_impact(self, amount: float, levels: List, side: str) -> float:
        """Calculate market impact given order book levels"""
        if not levels:
            return 0.0
        
        remaining_amount = amount
        weighted_price = 0.0
        first_level_price = float(levels[0]['px']) if levels else 0.0
        
        if first_level_price <= 0:
            return 0.0
        
        for level in levels:
            price = float(level['px'])
            size = float(level['sz'])
            
            if remaining_amount <= 0:
                break
            
            fill_amount = min(remaining_amount, size)
            weighted_price += price * fill_amount
            remaining_amount -= fill_amount
        
        if amount <= 0:
            return 0.0
        
        avg_fill_price = weighted_price / (amount - remaining_amount)
        slippage = abs(avg_fill_price - first_level_price) / first_level_price
        
        return slippage * 10000  # Return in basis points
    
    def detect_arbitrage_opportunity(self, token: str, spot_price: float, perp_price: float,
                                   funding_rate: Optional[float] = None) -> Optional[Dict]:
        """Detect arbitrage opportunities between spot and perp prices"""
        try:
            if spot_price <= 0 or perp_price <= 0:
                return None
            
            spread_bps = self.calculate_spread_bps(spot_price, perp_price)
            
            if abs(spread_bps) < self.min_spread_bps:
                return None  # Spread too small
            
            # Determine strategy based on spread direction
            if spread_bps > 0:
                # Perp price > Spot price: Long spot, Short perp
                strategy = "long_spot_short_perp"
                direction = "bearish_perp"
            else:
                # Spot price > Perp price: Short spot, Long perp
                strategy = "short_spot_long_perp"
                direction = "bullish_perp"
            
            # Estimate potential PnL (simplified calculation)
            estimated_pnl = self._estimate_arbitrage_pnl(
                spot_price, perp_price, spread_bps, funding_rate
            )
            
            opportunity = {
                "token": token,
                "spot_price": spot_price,
                "perp_price": perp_price,
                "spread_bps": spread_bps,
                "strategy": strategy,
                "direction": direction,
                "estimated_pnl": estimated_pnl,
                "funding_rate": funding_rate,
                "significance": "high" if abs(spread_bps) > self.significant_spread_bps else "medium",
                "timestamp": datetime.utcnow()
            }
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error detecting arbitrage opportunity for {token}: {e}")
            return None
    
    def _estimate_arbitrage_pnl(self, spot_price: float, perp_price: float, 
                              spread_bps: float, funding_rate: Optional[float]) -> float:
        """Estimate potential PnL from arbitrage strategy"""
        try:
            # Base PnL from price difference (assumes $1000 position)
            position_size = 1000
            base_pnl = position_size * (abs(spread_bps) / 10000)
            
            # Adjust for funding costs if available
            funding_cost = 0.0
            if funding_rate is not None:
                # Estimate daily funding cost (funding typically occurs every 8 hours)
                daily_funding = funding_rate * 3  # 3 funding periods per day
                funding_cost = position_size * abs(daily_funding)
            
            # Subtract estimated transaction costs (0.05% each side)
            transaction_costs = position_size * 0.001  # 0.1% total
            
            estimated_pnl = base_pnl - funding_cost - transaction_costs
            
            return round(estimated_pnl, 2)
            
        except Exception as e:
            logger.error(f"Error estimating arbitrage PnL: {e}")
            return 0.0
    
    def analyze_funding_rate_trend(self, token: str, hours: int = 24) -> Dict:
        """Analyze funding rate trends for a token"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            funding_rates = db.session.query(FundingRate).filter(
                FundingRate.token == token,
                FundingRate.timestamp >= cutoff_time
            ).order_by(FundingRate.timestamp).all()
            
            if len(funding_rates) < 2:
                return {"error": "Insufficient funding rate data"}
            
            rates = [fr.funding_rate for fr in funding_rates]
            timestamps = [fr.timestamp for fr in funding_rates]
            
            # Convert to pandas for easier analysis
            df = pd.DataFrame({
                'timestamp': timestamps,
                'funding_rate': rates
            })
            
            # Calculate statistics
            current_rate = rates[-1]
            avg_rate = np.mean(rates)
            std_rate = np.std(rates)
            min_rate = np.min(rates)
            max_rate = np.max(rates)
            
            # Trend analysis
            if len(rates) >= 5:
                recent_trend = np.polyfit(range(len(rates[-5:])), rates[-5:], 1)[0]
            else:
                recent_trend = 0
            
            return {
                "token": token,
                "current_funding_rate": current_rate,
                "average_funding_rate": avg_rate,
                "funding_rate_std": std_rate,
                "min_funding_rate": min_rate,
                "max_funding_rate": max_rate,
                "recent_trend": recent_trend,
                "trend_direction": "increasing" if recent_trend > 0 else "decreasing" if recent_trend < 0 else "stable",
                "data_points": len(rates),
                "time_period_hours": hours
            }
            
        except Exception as e:
            logger.error(f"Error analyzing funding rate trend for {token}: {e}")
            return {"error": str(e)}
    
    def calculate_rolling_basis(self, token: str, window_hours: int = 24) -> Dict:
        """Calculate rolling basis between spot and perp prices"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
            
            # Get spot prices
            spot_prices = db.session.query(PriceData).filter(
                PriceData.token == token,
                PriceData.price_type == 'spot',
                PriceData.timestamp >= cutoff_time
            ).order_by(PriceData.timestamp).all()
            
            # Get perp prices
            perp_prices = db.session.query(PriceData).filter(
                PriceData.token == token,
                PriceData.price_type == 'mark',
                PriceData.timestamp >= cutoff_time
            ).order_by(PriceData.timestamp).all()
            
            if len(spot_prices) < 5 or len(perp_prices) < 5:
                return {"error": "Insufficient price data for basis calculation"}
            
            # Create DataFrames
            spot_df = pd.DataFrame([{
                'timestamp': p.timestamp,
                'spot_price': p.price
            } for p in spot_prices])
            
            perp_df = pd.DataFrame([{
                'timestamp': p.timestamp,
                'perp_price': p.price
            } for p in perp_prices])
            
            # Merge on timestamp (approximate matching within 1 minute)
            spot_df['timestamp_round'] = spot_df['timestamp'].dt.round('1min')
            perp_df['timestamp_round'] = perp_df['timestamp'].dt.round('1min')
            
            merged_df = pd.merge(spot_df, perp_df, on='timestamp_round', how='inner')
            
            if len(merged_df) < 5:
                return {"error": "Insufficient matching price data"}
            
            # Calculate basis
            merged_df['basis'] = (merged_df['perp_price'] - merged_df['spot_price']) / merged_df['spot_price']
            merged_df['basis_bps'] = merged_df['basis'] * 10000
            
            # Rolling statistics
            merged_df['rolling_basis_mean'] = merged_df['basis_bps'].rolling(window=10, min_periods=5).mean()
            merged_df['rolling_basis_std'] = merged_df['basis_bps'].rolling(window=10, min_periods=5).std()
            
            current_basis = merged_df['basis_bps'].iloc[-1] if len(merged_df) > 0 else 0
            avg_basis = merged_df['basis_bps'].mean()
            basis_std = merged_df['basis_bps'].std()
            
            return {
                "token": token,
                "current_basis_bps": current_basis,
                "average_basis_bps": avg_basis,
                "basis_std_bps": basis_std,
                "basis_range": [merged_df['basis_bps'].min(), merged_df['basis_bps'].max()],
                "data_points": len(merged_df),
                "time_period_hours": window_hours
            }
            
        except Exception as e:
            logger.error(f"Error calculating rolling basis for {token}: {e}")
            return {"error": str(e)}
    
    def get_market_summary(self, tokens: List[str]) -> Dict:
        """Get comprehensive market summary for given tokens"""
        try:
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "tokens": {},
                "overall_stats": {}
            }
            
            active_opportunities = 0
            total_spread_bps = 0
            
            for token in tokens:
                token_data = {}
                
                # Get latest prices
                latest_spot = db.session.query(PriceData).filter(
                    PriceData.token == token,
                    PriceData.price_type == 'spot'
                ).order_by(PriceData.timestamp.desc()).first()
                
                latest_perp = db.session.query(PriceData).filter(
                    PriceData.token == token,
                    PriceData.price_type == 'mark'
                ).order_by(PriceData.timestamp.desc()).first()
                
                latest_funding = db.session.query(FundingRate).filter(
                    FundingRate.token == token
                ).order_by(FundingRate.timestamp.desc()).first()
                
                if latest_spot and latest_perp:
                    spread_bps = self.calculate_spread_bps(latest_spot.price, latest_perp.price)
                    
                    token_data = {
                        "spot_price": latest_spot.price,
                        "perp_price": latest_perp.price,
                        "spread_bps": spread_bps,
                        "funding_rate": latest_funding.funding_rate if latest_funding else None,
                        "last_update": max(latest_spot.timestamp, latest_perp.timestamp).isoformat()
                    }
                    
                    if abs(spread_bps) > self.min_spread_bps:
                        active_opportunities += 1
                        total_spread_bps += abs(spread_bps)
                
                summary["tokens"][token] = token_data
            
            # Overall statistics
            summary["overall_stats"] = {
                "active_opportunities": active_opportunities,
                "average_abs_spread_bps": total_spread_bps / max(active_opportunities, 1),
                "tokens_monitored": len(tokens),
                "tokens_with_data": len([t for t in summary["tokens"].values() if t])
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return {"error": str(e)}
    
    def save_arbitrage_opportunity(self, opportunity: Dict) -> bool:
        """Save detected arbitrage opportunity to database"""
        try:
            arb_op = ArbitrageOpportunity(
                token=opportunity['token'],
                spot_price=opportunity['spot_price'],
                perp_price=opportunity['perp_price'],
                spread_bps=opportunity['spread_bps'],
                estimated_pnl=opportunity.get('estimated_pnl'),
                strategy=opportunity['strategy']
            )
            
            db.session.add(arb_op)
            db.session.commit()
            
            logger.info(f"Saved arbitrage opportunity for {opportunity['token']}: {opportunity['spread_bps']:.2f} bps")
            return True
            
        except Exception as e:
            logger.error(f"Error saving arbitrage opportunity: {e}")
            db.session.rollback()
            return False
