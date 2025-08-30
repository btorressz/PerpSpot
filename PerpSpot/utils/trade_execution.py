import asyncio
import random
import time
import logging
import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class TradeExecution:
    """Trade execution result with latency and funding details"""
    success: bool
    execution_time_ms: int
    slippage_pct: float
    executed_price: float
    requested_price: float
    funding_accrued: float
    fees: float
    net_result: float
    execution_mode: str
    timestamp: int

class ExecutionLatencyModel:
    """Model execution latency and network delays for realistic trade simulation"""
    
    def __init__(self):
        self.latency_profiles = {
            'fast': {
                'min_latency_ms': 5,
                'max_latency_ms': 25,
                'slippage_multiplier': 1.0,
                'stale_quote_probability': 0.01
            },
            'slow': {
                'min_latency_ms': 100,
                'max_latency_ms': 800,
                'slippage_multiplier': 2.5,
                'stale_quote_probability': 0.15
            }
        }
    
    def simulate_latency(self, mode: str = 'fast') -> Tuple[int, bool]:
        """Simulate network latency and determine if quote is stale"""
        profile = self.latency_profiles.get(mode, self.latency_profiles['fast'])
        
        latency_ms = random.randint(
            profile['min_latency_ms'], 
            profile['max_latency_ms']
        )
        
        is_stale = random.random() < profile['stale_quote_probability']
        
        return latency_ms, is_stale
    
    def calculate_slippage(self, 
                          base_slippage: float, 
                          mode: str, 
                          is_stale: bool) -> float:
        """Calculate slippage based on latency mode and quote freshness"""
        profile = self.latency_profiles.get(mode, self.latency_profiles['fast'])
        
        # Base slippage adjusted by mode
        adjusted_slippage = base_slippage * profile['slippage_multiplier']
        
        # Additional slippage for stale quotes
        if is_stale:
            adjusted_slippage += random.uniform(0.1, 0.5)  # 0.1-0.5% additional
            
        return adjusted_slippage

class FundingCompoundingCalculator:
    """Calculate funding rate compounding over time with exponential decay"""
    
    def __init__(self):
        self.funding_logs = []
    
    def calculate_accrued_funding(self, 
                                 position_size: float,
                                 entry_price: float,
                                 funding_rate_annual: float,
                                 holding_time_hours: float,
                                 compounding_frequency_hours: float = 1.0) -> Dict:
        """
        Calculate accrued funding with hourly compounding
        
        Args:
            position_size: Size of position
            entry_price: Entry price
            funding_rate_annual: Annual funding rate (e.g., 0.1 for 10%)
            holding_time_hours: How long position is held
            compounding_frequency_hours: How often funding compounds (default 1 hour)
        """
        
        # Convert annual rate to hourly rate
        hourly_rate = funding_rate_annual / (365 * 24)
        
        # Number of compounding periods
        periods = int(holding_time_hours / compounding_frequency_hours)
        remaining_hours = holding_time_hours % compounding_frequency_hours
        
        # Initial notional value
        notional_value = position_size * entry_price
        current_funding_accrued = 0.0
        
        funding_log = []
        
        # Calculate compounded funding for full periods
        for period in range(periods):
            period_funding = notional_value * hourly_rate * compounding_frequency_hours
            current_funding_accrued += period_funding
            
            # Log funding for analytics
            period_start = period * compounding_frequency_hours
            funding_log.append({
                'period': period + 1,
                'hours_elapsed': period_start + compounding_frequency_hours,
                'period_funding': period_funding,
                'cumulative_funding': current_funding_accrued,
                'effective_rate': (current_funding_accrued / notional_value) * 100
            })
        
        # Calculate funding for remaining partial period
        if remaining_hours > 0:
            partial_funding = notional_value * hourly_rate * remaining_hours
            current_funding_accrued += partial_funding
            
            funding_log.append({
                'period': periods + 1,
                'hours_elapsed': holding_time_hours,
                'period_funding': partial_funding,
                'cumulative_funding': current_funding_accrued,
                'effective_rate': (current_funding_accrued / notional_value) * 100
            })
        
        # Calculate effective annual rate with compounding
        if holding_time_hours > 0:
            effective_annual_rate = (current_funding_accrued / notional_value) * (8760 / holding_time_hours)
        else:
            effective_annual_rate = 0
        
        result = {
            'total_funding_accrued': current_funding_accrued,
            'effective_annual_rate': effective_annual_rate,
            'periods_calculated': len(funding_log),
            'funding_log': funding_log,
            'position_details': {
                'position_size': position_size,
                'entry_price': entry_price,
                'notional_value': notional_value,
                'holding_time_hours': holding_time_hours
            }
        }
        
        # Store in class logs for analytics
        self.funding_logs.append({
            'timestamp': int(time.time() * 1000),
            'calculation': result
        })
        
        return result
    
    def get_funding_analytics(self, hours: int = 24) -> Dict:
        """Get funding calculation analytics for the past N hours"""
        cutoff_time = int(time.time() * 1000) - (hours * 60 * 60 * 1000)
        recent_logs = [log for log in self.funding_logs if log['timestamp'] >= cutoff_time]
        
        if not recent_logs:
            return {}
        
        total_calculations = len(recent_logs)
        total_funding = sum(log['calculation']['total_funding_accrued'] for log in recent_logs)
        avg_effective_rate = sum(log['calculation']['effective_annual_rate'] for log in recent_logs) / total_calculations
        
        return {
            'total_calculations': total_calculations,
            'total_funding_accrued': total_funding,
            'average_effective_annual_rate': avg_effective_rate,
            'time_period_hours': hours
        }

class TradeExecutor:
    """Main trade executor with latency modeling and funding calculations"""
    
    def __init__(self):
        self.latency_model = ExecutionLatencyModel()
        self.funding_calculator = FundingCompoundingCalculator()
        self.execution_history = []
    
    async def execute_trade(self,
                           trade_type: str,  # 'spot' or 'perp'
                           token: str,
                           size: float,
                           expected_price: float,
                           base_slippage: float = 0.1,
                           execution_mode: str = 'fast',
                           funding_rate_annual: float = 0.0,
                           holding_time_hours: float = 0.0) -> TradeExecution:
        """
        Execute trade with latency modeling and funding calculations
        
        Args:
            trade_type: 'spot' or 'perp'
            token: Token symbol
            size: Trade size
            expected_price: Expected execution price
            base_slippage: Base slippage percentage
            execution_mode: 'fast' or 'slow'
            funding_rate_annual: Annual funding rate for perp trades
            holding_time_hours: Expected holding time for funding calculation
        """
        
        start_time = time.time()
        
        try:
            # Simulate network latency
            latency_ms, is_stale = self.latency_model.simulate_latency(execution_mode)
            
            # Simulate network delay
            await asyncio.sleep(latency_ms / 1000)
            
            # Calculate slippage
            slippage_pct = self.latency_model.calculate_slippage(
                base_slippage, execution_mode, is_stale
            )
            
            # Calculate executed price with slippage
            if trade_type == 'spot':
                # For spot trades, slippage increases price
                executed_price = expected_price * (1 + slippage_pct / 100)
            else:
                # For perp trades, slippage can go either way
                slippage_direction = 1 if random.random() > 0.5 else -1
                executed_price = expected_price * (1 + (slippage_direction * slippage_pct / 100))
            
            # Calculate fees
            if trade_type == 'spot':
                fee_rate = 0.003  # 0.3% for spot (Jupiter average)
            else:
                fee_rate = 0.0002  # 0.02% for perp (Hyperliquid maker)
            
            fees = size * executed_price * fee_rate
            
            # Calculate funding for perpetual trades
            funding_accrued = 0.0
            if trade_type == 'perp' and holding_time_hours > 0:
                funding_result = self.funding_calculator.calculate_accrued_funding(
                    position_size=size,
                    entry_price=executed_price,
                    funding_rate_annual=funding_rate_annual,
                    holding_time_hours=holding_time_hours
                )
                funding_accrued = funding_result['total_funding_accrued']
            
            # Calculate net result
            price_diff = (executed_price - expected_price) * size
            net_result = -price_diff - fees - funding_accrued
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            execution = TradeExecution(
                success=True,
                execution_time_ms=execution_time_ms,
                slippage_pct=slippage_pct,
                executed_price=executed_price,
                requested_price=expected_price,
                funding_accrued=funding_accrued,
                fees=fees,
                net_result=net_result,
                execution_mode=execution_mode,
                timestamp=int(time.time() * 1000)
            )
            
            # Store execution history
            self.execution_history.append({
                'trade_type': trade_type,
                'token': token,
                'size': size,
                'execution': execution
            })
            
            logger.info(f"Trade executed: {trade_type} {token} {size} @ {executed_price:.4f} "
                       f"(slippage: {slippage_pct:.2f}%, latency: {latency_ms}ms)")
            
            return execution
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return TradeExecution(
                success=False,
                execution_time_ms=int((time.time() - start_time) * 1000),
                slippage_pct=0,
                executed_price=expected_price,
                requested_price=expected_price,
                funding_accrued=0,
                fees=0,
                net_result=0,
                execution_mode=execution_mode,
                timestamp=int(time.time() * 1000)
            )
    
    def get_execution_stats(self, hours: int = 24) -> Dict:
        """Get execution statistics for the past N hours"""
        cutoff_time = int(time.time() * 1000) - (hours * 60 * 60 * 1000)
        recent_executions = [
            exec_data for exec_data in self.execution_history
            if exec_data['execution'].timestamp >= cutoff_time
        ]
        
        if not recent_executions:
            return {}
        
        successful_executions = [ex for ex in recent_executions if ex['execution'].success]
        
        if not successful_executions:
            return {'total_executions': len(recent_executions), 'successful_executions': 0}
        
        avg_slippage = sum(ex['execution'].slippage_pct for ex in successful_executions) / len(successful_executions)
        avg_latency = sum(ex['execution'].execution_time_ms for ex in successful_executions) / len(successful_executions)
        total_fees = sum(ex['execution'].fees for ex in successful_executions)
        total_funding = sum(ex['execution'].funding_accrued for ex in successful_executions)
        
        return {
            'total_executions': len(recent_executions),
            'successful_executions': len(successful_executions),
            'success_rate': len(successful_executions) / len(recent_executions),
            'average_slippage_pct': avg_slippage,
            'average_latency_ms': avg_latency,
            'total_fees': total_fees,
            'total_funding_accrued': total_funding,
            'time_period_hours': hours
        }

# Global trade executor instance
trade_executor = TradeExecutor()

# Convenience functions for easy access
async def execute_spot_trade(token: str, 
                           size: float, 
                           expected_price: float,
                           mode: str = 'fast') -> TradeExecution:
    """Execute a spot trade with latency simulation"""
    return await trade_executor.execute_trade(
        trade_type='spot',
        token=token,
        size=size,
        expected_price=expected_price,
        execution_mode=mode
    )

async def execute_perp_trade(token: str,
                           size: float,
                           expected_price: float,
                           funding_rate: float,
                           holding_hours: float = 24.0,
                           mode: str = 'fast') -> TradeExecution:
    """Execute a perpetual trade with funding calculation"""
    return await trade_executor.execute_trade(
        trade_type='perp',
        token=token,
        size=size,
        expected_price=expected_price,
        execution_mode=mode,
        funding_rate_annual=funding_rate,
        holding_time_hours=holding_hours
    )

def calculate_funding_for_position(position_size: float,
                                 entry_price: float,
                                 funding_rate_annual: float,
                                 holding_time_hours: float) -> Dict:
    """Calculate funding for an existing position"""
    return trade_executor.funding_calculator.calculate_accrued_funding(
        position_size=position_size,
        entry_price=entry_price,
        funding_rate_annual=funding_rate_annual,
        holding_time_hours=holding_time_hours
    )

def get_execution_analytics() -> Dict:
    """Get comprehensive execution analytics"""
    return {
        'execution_stats_24h': trade_executor.get_execution_stats(24),
        'execution_stats_1h': trade_executor.get_execution_stats(1),
        'funding_analytics_24h': trade_executor.funding_calculator.get_funding_analytics(24)
    }