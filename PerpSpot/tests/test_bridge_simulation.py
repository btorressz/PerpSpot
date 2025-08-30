"""
Unit tests for Monte Carlo bridge simulation functionality.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bridge_service import BridgeArbitrageService


class TestBridgeSimulation(unittest.TestCase):
    """Test cases for bridge Monte Carlo simulation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.bridge_service = BridgeArbitrageService()
    
    def test_monte_carlo_simulation_basic(self):
        """Test basic Monte Carlo simulation functionality"""
        # Run simulation with 100 iterations for speed
        result = self.bridge_service.simulate_bridge_execution_monte_carlo(
            token='SOL',
            notional_usd=1000.0,
            n_sims=100
        )
        
        # Verify response structure
        self.assertIn('simulation_stats', result)
        self.assertIn('input_parameters', result)
        
        stats = result['simulation_stats']
        
        # Verify all required statistics are present
        required_keys = [
            'n_simulations', 'mean_pnl', 'median_pnl', 
            'pnl_95pctile', 'pnl_5pctile', 'success_probability',
            'avg_exec_ms', 'p99_exec_ms', 'sample_draws'
        ]
        
        for key in required_keys:
            self.assertIn(key, stats, f"Missing required key: {key}")
        
        # Verify types and ranges
        self.assertEqual(stats['n_simulations'], 100)
        self.assertIsInstance(stats['mean_pnl'], float)
        self.assertIsInstance(stats['success_probability'], float)
        self.assertGreaterEqual(stats['success_probability'], 0.0)
        self.assertLessEqual(stats['success_probability'], 1.0)
        
        # Verify sample draws structure
        self.assertIsInstance(stats['sample_draws'], list)
        self.assertGreater(len(stats['sample_draws']), 0)
        
        sample = stats['sample_draws'][0]
        self.assertIn('pnl_usd', sample)
        self.assertIn('exec_time_ms', sample)
        self.assertIn('success', sample)
        self.assertIsInstance(sample['success'], bool)
    
    def test_monte_carlo_with_template(self):
        """Test simulation with execution template"""
        result = self.bridge_service.simulate_bridge_execution_monte_carlo(
            token='ETH',
            notional_usd=2000.0,
            template='SOL Scalping',
            n_sims=50
        )
        
        self.assertIn('simulation_stats', result)
        self.assertEqual(result['simulation_stats']['n_simulations'], 50)
        
        # Verify input parameters include template
        params = result['input_parameters']
        self.assertEqual(params['template'], 'SOL Scalping')
        self.assertEqual(params['token'], 'ETH')
        self.assertEqual(params['notional_usd'], 2000.0)
    
    def test_monte_carlo_price_overrides(self):
        """Test simulation with price overrides"""
        jupiter_price = 150.0
        hyperliquid_price = 151.5
        funding_rate = 0.0002
        
        result = self.bridge_service.simulate_bridge_execution_monte_carlo(
            token='BTC',
            notional_usd=10000.0,
            jupiter_price=jupiter_price,
            hyperliquid_price=hyperliquid_price,
            funding_rate=funding_rate,
            n_sims=25
        )
        
        params = result['input_parameters']
        self.assertEqual(params['jupiter_price'], jupiter_price)
        self.assertEqual(params['hyperliquid_price'], hyperliquid_price)
        self.assertEqual(params['funding_rate'], funding_rate)
        
        # Verify spread calculation
        expected_spread_bps = abs(jupiter_price - hyperliquid_price) / jupiter_price * 10000
        self.assertAlmostEqual(params['spread_bps'], expected_spread_bps, places=2)
    
    def test_monte_carlo_n_sims_limit(self):
        """Test that n_sims is properly limited"""
        # Request more than 5000 simulations
        result = self.bridge_service.simulate_bridge_execution_monte_carlo(
            token='SOL',
            notional_usd=1000.0,
            n_sims=10000  # Should be capped at 5000
        )
        
        # Verify it was capped
        self.assertLessEqual(result['simulation_stats']['n_simulations'], 5000)
    
    def test_monte_carlo_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test with invalid token (should still work with demo data)
        result = self.bridge_service.simulate_bridge_execution_monte_carlo(
            token='INVALID',
            notional_usd=1000.0,
            n_sims=10
        )
        
        # Should handle gracefully
        self.assertIn('simulation_stats', result)


class TestBridgeIntegration(unittest.TestCase):
    """Integration tests for bridge service"""
    
    def test_template_management(self):
        """Test execution template management"""
        bridge_service = BridgeArbitrageService()
        
        # Get templates
        templates = bridge_service.get_execution_templates()
        self.assertIsInstance(templates, list)
        self.assertGreater(len(templates), 0)
        
        # Verify template structure
        template = templates[0]
        required_fields = ['name', 'token_pair', 'trade_size', 'max_latency', 'min_spread_bps']
        for field in required_fields:
            self.assertIn(field, template)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)