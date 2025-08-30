from flask import Blueprint, jsonify, request
import logging
import time

logger = logging.getLogger(__name__)

# Import cache service for statistics
try:
    from services.cache_service import cache_service
except ImportError:
    cache_service = None

# Import bridge service for cross-protocol arbitrage
try:
    from services.bridge_service import bridge_service
except ImportError:
    bridge_service = None

# Import PnL service for position simulation
try:
    from services.pnl_service import pnl_service
except ImportError:
    pnl_service = None

# Import slippage model for market impact calculations
try:
    from services.slippage_model import slippage_model
except ImportError:
    slippage_model = None

api_bp = Blueprint('api', __name__)

def get_arbitrage_service():
    """Get arbitrage service instance"""
    try:
        from app import arbitrage_service
        return arbitrage_service
    except ImportError:
        logger.error("Could not import arbitrage service")
        return None

@api_bp.route('/prices')
def get_prices():
    """Get current prices for all tokens"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        token = request.args.get('token')
        if token:
            price_data = arbitrage_service.get_price_data(token)
        else:
            price_data = arbitrage_service.get_price_data()
        return jsonify({
            'success': True,
            'data': price_data,
            'timestamp': int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error in /prices endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/arbitrage')
def get_arbitrage_opportunities():
    """Get current arbitrage opportunities with slippage estimates"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        min_spread = request.args.get('min_spread', type=float)
        notional_size = float(request.args.get('notional', 1000))  # Default $1000
        
        if min_spread is not None:
            opportunities = arbitrage_service.get_arbitrage_opportunities(min_spread)
        else:
            opportunities = arbitrage_service.get_arbitrage_opportunities()
        
        # Enhance opportunities with slippage estimates
        if slippage_model and opportunities:
            for opp in opportunities:
                try:
                    slippage_bps = slippage_model.calculate_slippage(
                        token=opp.get('token', 'SOL'),
                        trade_size_usd=notional_size
                    )
                    opp['slippage_estimate_bps'] = slippage_bps
                except Exception as e:
                    logger.warning(f"Could not calculate slippage for {opp.get('token')}: {e}")
                    opp['slippage_estimate_bps'] = 0.0
        
        return jsonify({
            'success': True,
            'data': opportunities,
            'count': len(opportunities),
            'timestamp': int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error in /arbitrage endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/bridge/simulate')
def simulate_bridge_execution():
    """
    Monte Carlo simulation endpoint for bridge arbitrage execution.
    
    Query Parameters:
        token (str): Token symbol (required, e.g., 'SOL', 'ETH', 'BTC')
        notional (float): Notional USD trade size (required)
        template (str): Execution template name (optional)
        n_sims (int): Number of simulations (optional, default 1000, max 5000)
        jupiter_price (float): Override Jupiter price (optional)
        hyperliquid_price (float): Override Hyperliquid price (optional)
        funding_rate (float): Override funding rate (optional)
        
    Returns:
        JSON response with simulation statistics including:
        - mean_pnl, median_pnl: Central tendency measures
        - pnl_95pctile, pnl_5pctile: Risk percentiles 
        - success_probability: Fraction of profitable simulations
        - avg_exec_ms, p99_exec_ms: Execution timing statistics
        - sample_draws: Sample of individual simulation results
    """
    try:
        # Get bridge service
        if not bridge_service:
            return jsonify({
                'success': False, 
                'error': 'Bridge service not available'
            }), 503
        
        # Parse required parameters
        token = request.args.get('token')
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token parameter is required'
            }), 400
            
        try:
            notional_usd = float(request.args.get('notional', 0))
            if notional_usd <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Notional USD amount must be positive'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid notional amount'
            }), 400
        
        # Parse optional parameters
        template = request.args.get('template')
        n_sims = min(int(request.args.get('n_sims', 1000)), 5000)  # Cap at 5k for performance
        
        # Optional price overrides
        jupiter_price = None
        hyperliquid_price = None
        funding_rate = None
        
        jupiter_price_str = request.args.get('jupiter_price')
        if jupiter_price_str:
            try:
                jupiter_price = float(jupiter_price_str)
            except ValueError:
                pass
                
        hyperliquid_price_str = request.args.get('hyperliquid_price')
        if hyperliquid_price_str:
            try:
                hyperliquid_price = float(hyperliquid_price_str)
            except ValueError:
                pass
                
        funding_rate_str = request.args.get('funding_rate')
        if funding_rate_str:
            try:
                funding_rate = float(funding_rate_str)
            except ValueError:
                pass
        
        # Run Monte Carlo simulation
        start_time = time.time()
        
        simulation_result = bridge_service.simulate_bridge_execution_monte_carlo(
            token=token.upper(),
            notional_usd=notional_usd,
            template=template,
            n_sims=n_sims,
            jupiter_price=jupiter_price,
            hyperliquid_price=hyperliquid_price,
            funding_rate=funding_rate
        )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Check if simulation had errors
        if 'error' in simulation_result:
            return jsonify({
                'success': False,
                'error': simulation_result['error'],
                'token': token,
                'notional_usd': notional_usd
            }), 500
        
        # Add execution metadata
        response_data = {
            'success': True,
            'simulation_stats': simulation_result.get('simulation_stats', {}),
            'input_parameters': simulation_result.get('input_parameters', {}),
            'execution_metadata': {
                'execution_time_ms': execution_time_ms,
                'server_timestamp': int(time.time() * 1000),
                'api_version': '1.0'
            }
        }
        
        logger.info(f"Monte Carlo simulation completed for {token}: {n_sims} runs, "
                   f"execution time: {execution_time_ms:.1f}ms")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in /bridge/simulate endpoint: {str(e)}")
        return jsonify({
            'success': False, 
            'error': 'Internal simulation error',
            'details': str(e)
        }), 500

@api_bp.route('/bridge-arb')
def bridge_arbitrage():
    """Enhanced bridge arbitrage analysis endpoint with query support"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        # Enhanced query parameters
        token = request.args.get('token', 'SOL')
        base = request.args.get('base', 'USDC')
        size = float(request.args.get('size', 1000))
        latency_mode = request.args.get('latency', 'fast')  # fast or slow
        
        # Get real-time prices
        price_data = arbitrage_service.get_price_data(token)
        if not price_data:
            return jsonify({
                'success': False,
                'error': f'No price data available for {token}'
            }), 404
        
        jupiter_data = price_data.get('jupiter', {})
        hyperliquid_data = price_data.get('hyperliquid', {})
        
        jupiter_price = jupiter_data.get('spot_price', 0) or jupiter_data.get('price', 0)
        hyperliquid_price = hyperliquid_data.get('mark_price', 0)
        
        if not jupiter_price or not hyperliquid_price:
            # For tokens not available on Hyperliquid, provide informative message
            if not hyperliquid_price and jupiter_price:
                return jsonify({
                    'success': False,
                    'error': f'{token} is not available on Hyperliquid perpetuals market. Try SOL, ETH, or BTC for cross-exchange arbitrage.'
                }), 400
            elif not jupiter_price and hyperliquid_price:
                return jsonify({
                    'success': False,
                    'error': f'{token} is not available on Jupiter spot market.'
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': f'Price data unavailable for {token} on both exchanges.'
                }), 400
        
        # Calculate real-time arbitrage delta
        spread_pct = ((hyperliquid_price - jupiter_price) / jupiter_price) * 100
        spread_abs = abs(spread_pct)
        
        # Calculate fees and slippage
        jupiter_fee = size * 0.003  # 0.3% average Jupiter fee
        hyperliquid_fee = size * 0.0002  # 0.02% Hyperliquid maker fee
        total_fees = jupiter_fee + hyperliquid_fee
        
        # Estimate slippage based on size and liquidity
        liquidity = jupiter_data.get('liquidity', 1000000)
        size_impact = min((size / liquidity) * 10000, 500)  # Max 5% slippage
        slippage_cost = size * (size_impact / 10000)
        
        # Simulate latency impact
        import random
        if latency_mode == 'slow':
            latency_ms = random.randint(100, 500)
            latency_cost = size * 0.001  # Additional 0.1% for stale quotes
        else:
            latency_ms = random.randint(10, 50)
            latency_cost = size * 0.0001  # Minimal latency cost
        
        # Calculate net profit
        gross_profit = (spread_pct / 100) * size
        net_profit = gross_profit - total_fees - slippage_cost - latency_cost
        roi_pct = (net_profit / (size * 0.1)) * 100 if size > 0 else 0  # Assuming 10x leverage
        
        # Get arbitrage opportunity for additional context
        opportunities = arbitrage_service.get_arbitrage_opportunities()
        token_opp = next((opp for opp in opportunities if opp['token'] == token), None)
        
        result = {
            'token': token,
            'base': base,
            'size': size,
            'prices': {
                'jupiter_price': jupiter_price,
                'hyperliquid_price': hyperliquid_price,
                'spread_pct': spread_pct,
                'spread_abs': spread_abs
            },
            'costs': {
                'jupiter_fee': jupiter_fee,
                'hyperliquid_fee': hyperliquid_fee,
                'total_fees': total_fees,
                'slippage_cost': slippage_cost,
                'latency_cost': latency_cost,
                'latency_ms': latency_ms
            },
            'profit': {
                'gross_profit': gross_profit,
                'net_profit': net_profit,
                'roi_pct': roi_pct,
                'profit_margin': (net_profit / size) * 100 if size > 0 else 0
            },
            'analysis': {
                'recommended_action': 'Execute' if net_profit > 10 else 'Monitor',
                'risk_level': 'Low' if spread_abs > 1.0 and liquidity > 1000000 else 'Medium',
                'confidence': min(spread_abs * 15, 95),
                'liquidity_score': min((liquidity / 10000000) * 100, 100)
            },
            'funding_rate': hyperliquid_data.get('funding_rate', 0),
            'opportunity': token_opp
        }
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /bridge-arb endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/simulate')
def simulate_trade():
    """Simulate a trade on Jupiter or Hyperliquid"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        platform = request.args.get('platform', 'jupiter')  # jupiter or hyperliquid
        token = request.args.get('token', 'SOL')
        amount = request.args.get('amount', 1.0, type=float)
        
        if platform.lower() == 'jupiter':
            from_token = request.args.get('from_token', 'USDC')
            result = arbitrage_service.jupiter.simulate_swap(from_token, token, amount)
        elif platform.lower() == 'hyperliquid':
            side = request.args.get('side', 'long')
            leverage = request.args.get('leverage', 1, type=int)
            result = arbitrage_service.hyperliquid.simulate_position(token, side, amount, leverage)
        else:
            return jsonify({'success': False, 'error': 'Invalid platform'}), 400
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /simulate endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/market-overview')
def market_overview():
    """Get overall market overview"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        overview = arbitrage_service.get_market_overview()
        
        return jsonify({
            'success': True,
            'data': overview,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /market-overview endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        # Check if services are responsive
        price_data = arbitrage_service.get_price_data()
        opportunities = arbitrage_service.get_arbitrage_opportunities()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'data': {
                'tokens_tracked': len(price_data) if price_data else 0,
                'opportunities_available': len(opportunities) if opportunities else 0,
                'last_update': max([data.get('last_updated', 0) for data in price_data.values()]) if price_data else 0
            },
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /health endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/execute')
def execute_trade():
    """Execute trade with latency modeling and funding calculation"""
    try:
        from utils.trade_execution import trade_executor
        
        trade_type = request.args.get('type', 'spot')  # spot or perp
        token = request.args.get('token', 'SOL')
        size = float(request.args.get('size', 1.0))
        expected_price = float(request.args.get('price', 150.0))
        execution_mode = request.args.get('mode', 'fast')  # fast or slow
        funding_rate = float(request.args.get('funding_rate', 0.0))
        holding_hours = float(request.args.get('holding_hours', 24.0))
        
        # This would normally execute the trade asynchronously
        # For now, return simulation data
        import asyncio
        import random
        
        # Simulate execution result
        slippage = random.uniform(0.05, 0.3) if execution_mode == 'fast' else random.uniform(0.2, 0.8)
        latency_ms = random.randint(10, 50) if execution_mode == 'fast' else random.randint(100, 500)
        executed_price = expected_price * (1 + slippage/100)
        
        fees = size * executed_price * (0.003 if trade_type == 'spot' else 0.0002)
        funding_cost = 0
        
        if trade_type == 'perp' and funding_rate != 0:
            # Simple funding calculation
            funding_cost = size * executed_price * funding_rate * (holding_hours / 8760)  # Annual to hourly
        
        net_result = (expected_price - executed_price) * size - fees - funding_cost
        
        return jsonify({
            'success': True,
            'execution': {
                'trade_type': trade_type,
                'token': token,
                'size': size,
                'expected_price': expected_price,
                'executed_price': executed_price,
                'slippage_pct': slippage,
                'execution_time_ms': latency_ms,
                'fees': fees,
                'funding_cost': funding_cost,
                'net_result': net_result,
                'execution_mode': execution_mode
            },
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /execute endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/funding-analytics')
def funding_analytics():
    """Get funding rate analytics and calculations"""
    try:
        token = request.args.get('token', 'SOL')
        position_size = float(request.args.get('size', 1.0))
        entry_price = float(request.args.get('entry_price', 150.0))
        holding_hours = float(request.args.get('holding_hours', 24.0))
        funding_rate = float(request.args.get('funding_rate', 0.1))  # 10% annual
        
        from utils.trade_execution import calculate_funding_for_position
        
        funding_result = calculate_funding_for_position(
            position_size=position_size,
            entry_price=entry_price,
            funding_rate_annual=funding_rate,
            holding_time_hours=holding_hours
        )
        
        return jsonify({
            'success': True,
            'data': funding_result,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /funding-analytics endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/execution-stats')
def execution_stats():
    """Get execution statistics and analytics"""
    try:
        from utils.trade_execution import get_execution_analytics
        
        analytics = get_execution_analytics()
        
        return jsonify({
            'success': True,
            'data': analytics,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /execution-stats endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/historical')
def historical_data():
    """Get historical arbitrage data for charting"""
    try:
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        hours = request.args.get('hours', 24, type=int)
        
        # Get current opportunities to generate historical-like data
        opportunities = arbitrage_service.get_arbitrage_opportunities()
        
        # Generate synthetic historical data points
        historical_data = []
        current_time = time.time() * 1000
        
        for i in range(min(20, max(len(opportunities), 5))):
            # Create data points going back in time
            timestamp = current_time - (i * 300000)  # 5 minute intervals
            
            if i < len(opportunities):
                max_spread = opportunities[i]['spread_abs']
                avg_spread = max_spread * 0.8
            else:
                # Generate some variation for demo
                import random
                max_spread = random.uniform(0.1, 2.0)
                avg_spread = max_spread * random.uniform(0.6, 0.9)
            
            historical_data.append({
                'timestamp': int(timestamp),
                'max_spread': max_spread,
                'avg_spread': avg_spread,
                'opportunities_count': len(opportunities)
            })
        
        # Sort by timestamp (oldest first)
        historical_data.sort(key=lambda x: x['timestamp'])
        
        return jsonify({
            'success': True,
            'data': historical_data,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /historical endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/cache/stats')
def get_cache_stats():
    """Get Redis cache statistics and performance metrics"""
    try:
        if not cache_service:
            return jsonify({
                'success': False,
                'error': 'Cache service not available'
            }), 503
        
        stats = cache_service.get_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error in /cache/stats endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/cache/flush', methods=['POST'])
def flush_cache():
    """Flush all Redis cache entries"""
    try:
        if not cache_service:
            return jsonify({
                'success': False,
                'error': 'Cache service not available'
            }), 503
        
        success = cache_service.flush_all()
        
        return jsonify({
            'success': success,
            'message': 'Cache flushed successfully' if success else 'Failed to flush cache',
            'timestamp': int(time.time() * 1000)
        })
    except Exception as e:
        logger.error(f"Error in /cache/flush endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== BRIDGE ARBITRAGE ENDPOINTS =====



@api_bp.route('/bridge/analytics')
def get_bridge_analytics():
    """Get comprehensive bridge arbitrage analytics"""
    try:
        if not bridge_service:
            return jsonify({
                'success': False,
                'error': 'Bridge service not available'
            }), 503
        
        time_window = int(request.args.get('hours', 24))
        token = request.args.get('token', 'SOL').upper()
        analytics = bridge_service.get_bridge_analytics(time_window, token)
        
        return jsonify({
            'success': True,
            'data': analytics,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /bridge/analytics endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/bridge/templates')
def get_execution_templates():
    """Get all execution templates"""
    try:
        if not bridge_service:
            return jsonify({
                'success': False,
                'error': 'Bridge service not available'
            }), 503
        
        templates = bridge_service.get_execution_templates()
        
        return jsonify({
            'success': True,
            'data': templates,
            'count': len(templates),
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /bridge/templates endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/bridge/templates', methods=['POST'])
def save_execution_template():
    """Save a new execution template"""
    try:
        if not bridge_service:
            return jsonify({
                'success': False,
                'error': 'Bridge service not available'
            }), 503
        
        template_data = request.get_json()
        if not template_data:
            return jsonify({'success': False, 'error': 'Template data required'}), 400
        
        success = bridge_service.save_execution_template(template_data)
        
        return jsonify({
            'success': success,
            'message': 'Template saved successfully' if success else 'Failed to save template',
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in POST /bridge/templates endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/bridge/templates/<template_name>', methods=['DELETE'])
def delete_execution_template(template_name):
    """Delete an execution template"""
    try:
        if not bridge_service:
            return jsonify({
                'success': False,
                'error': 'Bridge service not available'
            }), 503
        
        success = bridge_service.delete_execution_template(template_name)
        
        return jsonify({
            'success': success,
            'message': 'Template deleted successfully' if success else 'Template not found',
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in DELETE /bridge/templates endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/bridge/spread-history')
def get_historical_spread_bridges():
    """Get historical analysis of spread bridges and their duration"""
    try:
        if not bridge_service:
            return jsonify({
                'success': False,
                'error': 'Bridge service not available'
            }), 503
        
        token = request.args.get('token')
        hours = int(request.args.get('hours', 24))
        
        spread_bridges = bridge_service.get_historical_spread_bridges(token, hours)
        
        return jsonify({
            'success': True,
            'data': spread_bridges,
            'count': len(spread_bridges),
            'token_filter': token,
            'time_window_hours': hours,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /bridge/spread-history endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/bridge/unified-execution')
def unified_execution_analysis():
    """One-click unified execution analysis with comprehensive modeling"""
    try:
        if not bridge_service or not get_arbitrage_service():
            return jsonify({
                'success': False,
                'error': 'Required services not available'
            }), 503
        
        # Get all current opportunities
        arbitrage_service = get_arbitrage_service()
        opportunities = arbitrage_service.get_arbitrage_opportunities()
        
        if not opportunities:
            # Return demo opportunities for testing when no real ones available
            demo_opportunities = [
                {'token': 'SOL', 'spread_abs': 0.025, 'jupiter_price': 150.25, 'hyperliquid_price': 154.12, 'funding_rate': 0.0001},
                {'token': 'ETH', 'spread_abs': 0.018, 'jupiter_price': 2650.50, 'hyperliquid_price': 2698.75, 'funding_rate': 0.0002},
                {'token': 'BTC', 'spread_abs': 0.012, 'jupiter_price': 62500.00, 'hyperliquid_price': 63250.00, 'funding_rate': -0.0001}
            ]
            opportunities = demo_opportunities
        
        # Run unified analysis for top opportunities
        unified_results = []
        for opp in opportunities[:5]:  # Top 5 opportunities
            # Safely extract prices with fallbacks
            jupiter_price = opp.get('jupiter_price', opp.get('fallback_price', 100.0))
            hyperliquid_price = opp.get('hyperliquid_price', opp.get('fallback_price', 101.0))
            
            simulation = bridge_service.simulate_bridge_execution(
                token=opp['token'],
                size=1000.0,  # Standard size for comparison
                current_spread_bps=opp['spread_abs'] * 100,
                jupiter_price=jupiter_price,
                hyperliquid_price=hyperliquid_price,
                funding_rate=opp.get('funding_rate', 0.0)
            )
            
            if simulation and not simulation.get('error'):
                unified_results.append({
                    'token': opp['token'],
                    'opportunity_rank': len(unified_results) + 1,
                    'spread_bps': opp['spread_abs'] * 100,
                    'execution_analysis': simulation['execution_analysis'],
                    'risk_score': (
                        simulation['risk_metrics']['funding_risk_factor'] +
                        simulation['risk_metrics']['latency_risk_score']
                    ) / 2,
                    'simplified_signals': {
                        'entry_signal': 'BUY' if jupiter_price < hyperliquid_price else 'SELL',
                        'profit_potential': simulation['execution_analysis']['profit_margin_percent'],
                        'execution_time': simulation['execution_analysis']['expected_latency'],
                        'confidence': simulation['risk_metrics']['success_probability'] * 100
                    }
                })
        
        # Generate unified summary
        if unified_results:
            total_profit = sum(r['execution_analysis']['risk_adjusted_profit_usd'] for r in unified_results)
            avg_confidence = sum(r['simplified_signals']['confidence'] for r in unified_results) / len(unified_results)
            best_opportunity = max(unified_results, key=lambda x: x['execution_analysis']['profit_margin_percent'])
            
            unified_summary = {
                'total_opportunities_analyzed': len(unified_results),
                'total_potential_profit_usd': total_profit,
                'average_confidence_percent': avg_confidence,
                'best_opportunity': best_opportunity,
                'recommended_action': 'EXECUTE' if avg_confidence > 70 and total_profit > 50 else 'MONITOR',
                'market_efficiency_score': 100 - (len(unified_results) * 10)  # More opportunities = less efficient market
            }
        else:
            unified_summary = {
                'message': 'No viable opportunities after unified analysis',
                'recommended_action': 'WAIT'
            }
        
        return jsonify({
            'success': True,
            'data': {
                'unified_analysis': unified_summary,
                'detailed_opportunities': unified_results,
                'analysis_timestamp': int(time.time() * 1000)
            }
        })
        
    except Exception as e:
        logger.error(f"Error in /bridge/unified-execution endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/pnl/simulate')
def simulate_pnl():
    """
    Simulate position-level PnL with comprehensive cost analysis
    
    Query Parameters:
        token (str): Token symbol (required)
        entry_price (float): Entry execution price (required)
        exit_price (float): Exit execution price (required)
        position_size_usd (float): Position size in USD (required)
        position_type (str): "long" or "short" (default: "long")
        funding_rate (float): Hourly funding rate (default: 0.0)
        duration_hours (float): Position duration in hours (default: 1.0)
        slippage_bps (float): Total slippage in basis points (default: 0.0)
    """
    try:
        if not pnl_service:
            return jsonify({'success': False, 'error': 'PnL service not available'}), 503
        
        # Parse required parameters
        token = request.args.get('token')
        if not token:
            return jsonify({'success': False, 'error': 'Token parameter is required'}), 400
        
        try:
            entry_price = float(request.args.get('entry_price'))
            exit_price = float(request.args.get('exit_price'))
            position_size_usd = float(request.args.get('position_size_usd'))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid price or position size parameters'}), 400
        
        # Parse optional parameters
        position_type = request.args.get('position_type', 'long')
        funding_rate = float(request.args.get('funding_rate', 0.0))
        duration_hours = float(request.args.get('duration_hours', 1.0))
        slippage_bps = float(request.args.get('slippage_bps', 0.0))
        
        # Auto-calculate slippage if not provided and slippage model available
        if slippage_bps == 0.0 and slippage_model:
            try:
                slippage_bps = slippage_model.calculate_slippage(token, position_size_usd)
            except Exception as e:
                logger.warning(f"Could not auto-calculate slippage: {e}")
        
        # Run PnL simulation
        result = pnl_service.simulate_pnl(
            token=token.upper(),
            entry_price=entry_price,
            exit_price=exit_price,
            position_size_usd=position_size_usd,
            position_type=position_type,
            funding_rate=funding_rate,
            duration_hours=duration_hours,
            slippage_bps=slippage_bps
        )
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /pnl/simulate endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/funding/history')
def get_funding_history():
    """
    Get historical funding rate data with rolling averages
    
    Query Parameters:
        token (str): Token symbol (default: 'SOL')
        hours (int): Hours of history to retrieve (default: 24, max: 168)
    """
    try:
        token = request.args.get('token', 'SOL').upper()
        hours = min(int(request.args.get('hours', 24)), 168)  # Max 1 week
        
        # Try to get from cache first
        cache_key = f"funding_history_{token}_{hours}h"
        if cache_service:
            cached_data = cache_service.get_cached_data(cache_key)
            if cached_data:
                return jsonify({
                    'success': True,
                    'data': cached_data,
                    'source': 'cache',
                    'timestamp': int(time.time() * 1000)
                })
        
        # Generate demo funding rate history (replace with real data source)
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Create time series
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        time_range = pd.date_range(start=start_time, end=end_time, freq='H')
        
        # Generate realistic funding rates (hourly, typically -0.01% to +0.01%)
        np.random.seed(42)  # For consistent demo data
        base_rate = 0.0001  # 0.01% base rate
        rates = np.random.normal(base_rate, 0.00005, len(time_range))  # Small volatility
        
        # Create rolling averages
        rates_series = pd.Series(rates, index=time_range)
        rolling_24h = rates_series.rolling(window=24, min_periods=1).mean()
        
        # Format response
        funding_data = {
            'token': token,
            'hours_requested': hours,
            'data_points': len(time_range),
            'funding_rates': [
                {
                    'timestamp': int(ts.timestamp() * 1000),
                    'funding_rate': float(rate),
                    'funding_rate_24h_avg': float(avg_rate),
                    'funding_rate_bps': float(rate * 10000),  # Convert to basis points
                    'projected_8h_cost': float(rate * 8)  # 8-hour funding cost
                }
                for ts, rate, avg_rate in zip(time_range, rates, rolling_24h)
            ]
        }
        
        # Cache the result
        if cache_service:
            cache_service.set_cached_data(cache_key, funding_data, ttl=3600)  # 1 hour TTL
        
        return jsonify({
            'success': True,
            'data': funding_data,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /funding/history endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/arbitrage/zscore')
def get_spread_zscore():
    """
    Calculate rolling Z-score for price spreads
    
    Query Parameters:
        token (str): Token symbol (default: 'SOL')
        window (int): Rolling window for Z-score calculation (default: 60)
    """
    try:
        token = request.args.get('token', 'SOL').upper()
        window = int(request.args.get('window', 60))
        
        arbitrage_service = get_arbitrage_service()
        if not arbitrage_service:
            return jsonify({'success': False, 'error': 'Service not available'}), 503
        
        # Get current price data
        price_data = arbitrage_service.get_price_data(token)
        if not price_data:
            return jsonify({'success': False, 'error': f'No price data for {token}'}), 404
        
        # Generate historical spread data (demo implementation)
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Create demo spread time series
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        time_range = pd.date_range(start=start_time, end=end_time, freq='10min')
        
        # Get current spread as reference
        jupiter_price = price_data.get('jupiter', {}).get('spot_price', 100)
        hyperliquid_price = price_data.get('hyperliquid', {}).get('mark_price', 101)
        current_spread = hyperliquid_price - jupiter_price
        
        # Generate spread variations around current level
        np.random.seed(hash(token) % 1000)
        spread_variations = np.random.normal(current_spread, abs(current_spread) * 0.1, len(time_range))
        spreads = pd.Series(spread_variations, index=time_range)
        
        # Calculate rolling statistics
        rolling_mean = spreads.rolling(window=window, min_periods=1).mean()
        rolling_std = spreads.rolling(window=window, min_periods=1).std()
        
        # Calculate Z-scores
        z_scores = (spreads - rolling_mean) / rolling_std
        
        # Current Z-score
        current_zscore = z_scores.iloc[-1] if len(z_scores) > 0 else 0.0
        
        # Classification
        if abs(current_zscore) > 2:
            signal = "EXTREME"
            signal_strength = "HIGH"
        elif abs(current_zscore) > 1:
            signal = "SIGNIFICANT"
            signal_strength = "MEDIUM"
        else:
            signal = "NORMAL"
            signal_strength = "LOW"
        
        # Format response
        zscore_data = {
            'token': token,
            'current_spread': float(current_spread),
            'current_zscore': float(current_zscore),
            'signal': signal,
            'signal_strength': signal_strength,
            'rolling_window': window,
            'statistics': {
                'mean_spread': float(rolling_mean.iloc[-1]) if len(rolling_mean) > 0 else 0,
                'std_spread': float(rolling_std.iloc[-1]) if len(rolling_std) > 0 else 0,
                'min_zscore': float(z_scores.min()) if len(z_scores) > 0 else 0,
                'max_zscore': float(z_scores.max()) if len(z_scores) > 0 else 0
            },
            'time_series': [
                {
                    'timestamp': int(ts.timestamp() * 1000),
                    'spread': float(spread),
                    'zscore': float(zscore),
                    'rolling_mean': float(mean),
                    'rolling_std': float(std)
                }
                for ts, spread, zscore, mean, std in zip(
                    time_range[-50:], spreads[-50:], z_scores[-50:], 
                    rolling_mean[-50:], rolling_std[-50:]
                )
            ]
        }
        
        return jsonify({
            'success': True,
            'data': zscore_data,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /arbitrage/zscore endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/risk/var')
def calculate_var():
    """
    Calculate Value at Risk (VaR) for current positions or simulations
    
    Query Parameters:
        token (str): Token symbol (default: 'SOL')
        confidence_level (float): Confidence level (default: 0.05 for 95% VaR)
        position_size_usd (float): Position size for VaR calculation (default: 1000)
    """
    try:
        token = request.args.get('token', 'SOL').upper()
        confidence_level = float(request.args.get('confidence_level', 0.05))
        position_size_usd = float(request.args.get('position_size_usd', 1000))
        
        # Generate historical return data (demo implementation)
        import pandas as pd
        import numpy as np
        
        # Simulate daily returns based on token volatility
        volatility_map = {
            'SOL': 0.05, 'ETH': 0.04, 'BTC': 0.03,
            'JUP': 0.08, 'BONK': 0.12, 'ORCA': 0.07,
            'USDC': 0.001, 'USDT': 0.001, 'HL': 0.06
        }
        
        daily_vol = volatility_map.get(token, 0.05)
        np.random.seed(hash(token) % 1000)
        
        # Generate 100 days of returns
        returns = np.random.normal(0.0005, daily_vol, 100)  # Slight positive drift
        returns_series = pd.Series(returns)
        
        # Calculate VaR using multiple methods
        var_historical = returns_series.quantile(confidence_level)
        var_parametric = returns_series.mean() - 1.96 * returns_series.std()  # 95% normal VaR
        
        # Conditional VaR (Expected Shortfall)
        cvar = returns_series[returns_series <= var_historical].mean()
        
        # Convert to USD terms
        var_usd_historical = var_historical * position_size_usd
        var_usd_parametric = var_parametric * position_size_usd
        cvar_usd = cvar * position_size_usd
        
        # Risk metrics
        risk_data = {
            'token': token,
            'position_size_usd': position_size_usd,
            'confidence_level': confidence_level,
            'time_horizon': '1_day',
            'var_methods': {
                'historical': {
                    'var_percent': float(var_historical * 100),
                    'var_usd': float(var_usd_historical),
                    'description': 'Historical simulation VaR'
                },
                'parametric': {
                    'var_percent': float(var_parametric * 100),
                    'var_usd': float(var_usd_parametric),
                    'description': 'Normal distribution assumption VaR'
                }
            },
            'conditional_var': {
                'cvar_percent': float(cvar * 100),
                'cvar_usd': float(cvar_usd),
                'description': 'Expected loss given VaR breach'
            },
            'risk_statistics': {
                'daily_volatility': float(daily_vol * 100),
                'annualized_volatility': float(daily_vol * np.sqrt(365) * 100),
                'worst_day_return': float(returns_series.min() * 100),
                'best_day_return': float(returns_series.max() * 100),
                'sharpe_ratio': float(returns_series.mean() / returns_series.std())
            }
        }
        
        return jsonify({
            'success': True,
            'data': risk_data,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /risk/var endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/slippage-estimate')
def get_slippage_estimate():
    """Get slippage estimate for a given token and trade size"""
    try:
        token = request.args.get('token', 'SOL')
        size = float(request.args.get('size', 1000))
        
        if not slippage_model:
            return jsonify({
                'success': False,
                'error': 'Slippage model not available'
            }), 503
            
        # Calculate slippage using the slippage model
        slippage_bps = slippage_model.calculate_slippage(
            token=token,
            trade_size_usd=size
        )
        
        return jsonify({
            'success': True,
            'slippage_bps': slippage_bps,
            'token': token,
            'size': size,
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logger.error(f"Error in /slippage-estimate endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
