"""
Comprehensive unit tests for slippage and market impact models.
"""

import unittest
import math
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.slippage_model import SlippageModel, SlippageConfig, slippage_model


class TestSlippageModel(unittest.TestCase):
    """Test cases for slippage model functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = SlippageModel()
        self.test_config = SlippageConfig(
            k_sqrt=0.5,
            a_coeff=0.2,
            b_power=0.7
        )
    
    def test_square_root_slippage_basic(self):
        """Test basic square-root slippage calculation"""
        # Test with standard parameters
        notional = 10000  # $10k
        adv = 1000000     # $1M ADV
        
        slippage = self.model.estimate_slippage_by_notional(notional, adv)
        
        # Should be positive and reasonable
        self.assertGreater(slippage, 0)
        self.assertLess(slippage, 0.1)  # Less than 10%
        
        # Test mathematical relationship
        expected = 0.7 * math.sqrt(notional / adv)
        self.assertAlmostEqual(slippage, expected, places=4)
    
    def test_slippage_monotonicity(self):
        """Test that slippage increases monotonically with notional"""
        adv = 1000000  # $1M ADV
        test_sizes = [1000, 10000, 100000, 1000000]
        
        previous_slippage = 0
        for notional in test_sizes:
            slippage = self.model.estimate_slippage_by_notional(notional, adv)
            
            # Slippage should increase with trade size
            self.assertGreater(slippage, previous_slippage)
            previous_slippage = slippage
    
    def test_slippage_with_custom_k(self):
        """Test slippage calculation with custom k parameter"""
        notional = 50000
        adv = 2000000
        k_custom = 1.2
        
        slippage = self.model.estimate_slippage_by_notional(notional, adv, k=k_custom)
        expected = k_custom * math.sqrt(notional / adv)
        
        self.assertAlmostEqual(slippage, expected, places=4)
    
    def test_slippage_token_specific(self):
        """Test token-specific slippage adjustments"""
        notional = 25000
        adv = 500000
        
        # Test different tokens
        sol_slippage = self.model.estimate_slippage_by_notional(notional, adv, token='SOL')
        eth_slippage = self.model.estimate_slippage_by_notional(notional, adv, token='ETH')
        btc_slippage = self.model.estimate_slippage_by_notional(notional, adv, token='BTC')
        
        # All should be positive and reasonable
        for slippage in [sol_slippage, eth_slippage, btc_slippage]:
            self.assertGreater(slippage, 0)
            self.assertLess(slippage, 0.5)  # Less than 50%
    
    def test_almgren_chriss_model(self):
        """Test Almgren-Chriss impact estimation"""
        notional = 75000
        daily_vol = 5000000
        
        impact = self.model.estimate_almgren_chriss_impact(notional, daily_vol)
        
        # Should be positive and reasonable
        self.assertGreater(impact, 0)
        self.assertLess(impact, 0.1)  # Less than 10%
        
        # Test with custom parameters
        impact_custom = self.model.estimate_almgren_chriss_impact(
            notional, daily_vol, a=0.5, b=0.8
        )
        self.assertGreater(impact_custom, 0)
    
    def test_almgren_chriss_monotonicity(self):
        """Test Almgren-Chriss model monotonicity"""
        daily_vol = 10000000
        test_sizes = [5000, 25000, 100000, 500000]
        
        previous_impact = 0
        for notional in test_sizes:
            impact = self.model.estimate_almgren_chriss_impact(notional, daily_vol)
            
            # Impact should increase with trade size
            self.assertGreater(impact, previous_impact)
            previous_impact = impact
    
    def test_synthetic_depth_generation(self):
        """Test synthetic orderbook depth generation"""
        mid_price = 150.0
        depth = self.model.generate_synthetic_depth(
            mid_price, 
            spread_bps=20.0,
            depth_levels=5,
            base_size=500.0
        )
        
        # Verify structure
        self.assertIn('bids', depth)
        self.assertIn('asks', depth)
        self.assertEqual(len(depth['bids']), 5)
        self.assertEqual(len(depth['asks']), 5)
        
        # Verify price ordering
        bid_prices = [bid[0] for bid in depth['bids']]
        ask_prices = [ask[0] for ask in depth['asks']]
        
        # Bids should be descending
        self.assertEqual(bid_prices, sorted(bid_prices, reverse=True))
        
        # Asks should be ascending
        self.assertEqual(ask_prices, sorted(ask_prices))
        
        # Best bid should be below mid, best ask above
        self.assertLess(max(bid_prices), mid_price)
        self.assertGreater(min(ask_prices), mid_price)
    
    def test_depth_based_execution_list_format(self):
        """Test execution price estimation with list format depth"""
        size_token = 100.0
        current_price = 200.0
        
        # Create test depth as list of (price, size) tuples
        depth = [
            (201.0, 50.0),   # Best ask
            (202.0, 100.0),  # Second level
            (203.0, 200.0)   # Third level
        ]
        
        exec_price, slippage = self.model.estimate_execution_price_from_depth(
            size_token, depth, side='buy', current_price=current_price
        )
        
        # Should execute at weighted average: 50@201 + 50@202 = 201.5
        expected_price = (50 * 201.0 + 50 * 202.0) / 100
        self.assertAlmostEqual(exec_price, expected_price, places=2)
        
        # Slippage should be positive for buying
        self.assertGreater(slippage, 0)
        self.assertLess(slippage, 0.1)  # Should be reasonable
    
    def test_depth_based_execution_dict_format(self):
        """Test execution price estimation with dict format depth"""
        size_token = 75.0
        current_price = 100.0
        
        # Create test depth as dict
        depth = {
            'bids': [
                (99.5, 100.0),
                (99.0, 150.0),
                (98.5, 200.0)
            ],
            'asks': [
                (100.5, 80.0),
                (101.0, 120.0),
                (101.5, 180.0)
            ]
        }
        
        # Test buy order
        exec_price_buy, slippage_buy = self.model.estimate_execution_price_from_depth(
            size_token, depth, side='buy', current_price=current_price
        )
        
        # Test sell order
        exec_price_sell, slippage_sell = self.model.estimate_execution_price_from_depth(
            size_token, depth, side='sell', current_price=current_price
        )
        
        # Buy should execute higher than current price
        self.assertGreater(exec_price_buy, current_price)
        
        # Sell should execute lower than current price
        self.assertLess(exec_price_sell, current_price)
        
        # Both should have positive slippage
        self.assertGreater(slippage_buy, 0)
        self.assertGreater(slippage_sell, 0)
    
    def test_partial_fill_scenario(self):
        """Test execution when order size exceeds available depth"""
        size_token = 1000.0  # Large order
        current_price = 50.0
        
        # Limited depth
        depth = [
            (51.0, 200.0),
            (52.0, 300.0),
            (53.0, 400.0)  # Total: 900 tokens available
        ]
        
        exec_price, slippage = self.model.estimate_execution_price_from_depth(
            size_token, depth, side='buy', current_price=current_price
        )
        
        # Should have higher slippage due to partial fill penalty
        self.assertGreater(slippage, 0.05)  # At least 5% due to penalties
        
        # Execution price should be weighted average of all levels
        self.assertGreater(exec_price, 51.0)
        self.assertLess(exec_price, 53.0)
    
    def test_combined_slippage_estimation(self):
        """Test combined slippage estimation using multiple methods"""
        notional_usd = 50000
        token = 'ETH'
        adv_usd = 10000000
        current_price = 2500.0
        
        # Generate synthetic depth
        depth = self.model.generate_synthetic_depth(current_price, token=token)
        
        results = self.model.estimate_combined_slippage(
            notional_usd=notional_usd,
            token=token,
            adv_usd=adv_usd,
            depth=depth,
            current_price=current_price,
            side='buy'
        )
        
        # Verify required fields
        self.assertIn('recommended', results)
        self.assertIn('notional_usd', results)
        self.assertIn('token', results)
        
        # Should have multiple estimation methods
        estimation_methods = ['sqrt_model', 'almgren_chriss', 'depth_based']
        methods_found = sum(1 for method in estimation_methods if method in results)
        self.assertGreater(methods_found, 0)
        
        # Recommended slippage should be reasonable
        recommended = results['recommended']
        self.assertGreater(recommended, 0)
        self.assertLess(recommended, 0.2)  # Less than 20%
    
    def test_error_handling(self):
        """Test error handling for edge cases"""
        # Test with zero ADV
        slippage = self.model.estimate_slippage_by_notional(1000, 0)
        self.assertGreater(slippage, 0)  # Should fallback gracefully
        
        # Test with empty depth
        exec_price, slippage = self.model.estimate_execution_price_from_depth(
            100.0, [], current_price=100.0
        )
        self.assertGreater(exec_price, 0)
        self.assertGreater(slippage, 0)
        
        # Test with invalid depth format
        exec_price, slippage = self.model.estimate_execution_price_from_depth(
            100.0, "invalid", current_price=100.0
        )
        self.assertGreater(exec_price, 0)
        self.assertGreater(slippage, 0)
    
    def test_slippage_bounds(self):
        """Test that slippage estimates stay within reasonable bounds"""
        # Very large trade
        large_slippage = self.model.estimate_slippage_by_notional(
            10000000,  # $10M
            1000000    # $1M ADV (100% participation)
        )
        
        # Should be capped at max slippage
        self.assertLessEqual(large_slippage, self.model.config.max_slippage_bps / 10000)
        
        # Very small trade
        small_slippage = self.model.estimate_slippage_by_notional(
            100,       # $100
            100000000  # $100M ADV
        )
        
        # Should be at least min slippage
        self.assertGreaterEqual(small_slippage, self.model.config.min_slippage_bps / 10000)


class TestSlippageConfig(unittest.TestCase):
    """Test slippage configuration management"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = SlippageConfig()
        
        self.assertEqual(config.k_sqrt, 0.7)
        self.assertEqual(config.a_coeff, 0.3)
        self.assertEqual(config.b_power, 0.6)
        self.assertGreater(config.min_slippage_bps, 0)
        self.assertLess(config.max_slippage_bps, 1000)
    
    def test_custom_config(self):
        """Test custom configuration creation"""
        config = SlippageConfig(
            k_sqrt=1.0,
            a_coeff=0.5,
            b_power=0.8,
            min_slippage_bps=1.0,
            max_slippage_bps=200.0
        )
        
        model = SlippageModel(config)
        self.assertEqual(model.config.k_sqrt, 1.0)
        self.assertEqual(model.config.a_coeff, 0.5)


class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions"""
    
    def test_convenience_slippage_function(self):
        """Test convenience function for slippage estimation"""
        from services.slippage_model import estimate_slippage_by_notional
        
        slippage = estimate_slippage_by_notional(5000, 500000, k=0.8)
        
        self.assertGreater(slippage, 0)
        self.assertLess(slippage, 0.1)
    
    def test_convenience_depth_function(self):
        """Test convenience function for depth-based estimation"""
        from services.slippage_model import estimate_execution_price_from_depth
        
        depth = [(101.0, 100.0), (102.0, 200.0)]
        exec_price, slippage = estimate_execution_price_from_depth(150.0, depth)
        
        self.assertGreater(exec_price, 100.0)
        self.assertGreater(slippage, 0)


if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2)