"""
Slippage Model Demonstration Script

This script demonstrates the slippage estimation capabilities for various
trade sizes and tokens, showing how market impact scales with position size.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.slippage_model import SlippageModel, slippage_model


def format_percentage(value: float) -> str:
    """Format percentage value for display"""
    return f"{value * 100:.3f}%"


def format_bps(value: float) -> str:
    """Format basis points for display"""
    return f"{value * 10000:.1f} bps"


def demo_square_root_model():
    """Demonstrate square-root slippage model"""
    print("=" * 60)
    print("SQUARE-ROOT SLIPPAGE MODEL DEMONSTRATION")
    print("=" * 60)
    print("Formula: slippage = k * sqrt(notional / ADV)")
    print(f"Default k = {slippage_model.config.k_sqrt}")
    print()
    
    # Test different trade sizes
    test_sizes = [1_000, 10_000, 100_000]  # $1k, $10k, $100k
    adv_usd = 50_000_000  # $50M daily volume
    
    print(f"Assumed ADV: ${adv_usd:,}")
    print(f"{'Trade Size':<12} {'Participation':<15} {'Slippage':<12} {'Basis Points':<12}")
    print("-" * 60)
    
    for notional in test_sizes:
        participation = notional / adv_usd
        slippage = slippage_model.estimate_slippage_by_notional(notional, adv_usd)
        
        print(f"${notional:<10,} {participation:<15.4%} {format_percentage(slippage):<12} {format_bps(slippage):<12}")


def demo_almgren_chriss_model():
    """Demonstrate Almgren-Chriss impact model"""
    print("\n" + "=" * 60)
    print("ALMGREN-CHRISS IMPACT MODEL DEMONSTRATION")
    print("=" * 60)
    print("Formula: impact = a * (notional / daily_vol)^b")
    print(f"Default a = {slippage_model.config.a_coeff}, b = {slippage_model.config.b_power}")
    print()
    
    # Test different trade sizes
    test_sizes = [1_000, 10_000, 100_000]  # $1k, $10k, $100k
    daily_vol = 75_000_000  # $75M daily volume
    
    print(f"Assumed Daily Volume: ${daily_vol:,}")
    print(f"{'Trade Size':<12} {'Vol Ratio':<15} {'Impact':<12} {'Basis Points':<12}")
    print("-" * 60)
    
    for notional in test_sizes:
        vol_ratio = notional / daily_vol
        impact = slippage_model.estimate_almgren_chriss_impact(notional, daily_vol)
        
        print(f"${notional:<10,} {vol_ratio:<15.4%} {format_percentage(impact):<12} {format_bps(impact):<12}")


def demo_depth_based_execution():
    """Demonstrate depth-based execution price estimation"""
    print("\n" + "=" * 60)
    print("DEPTH-BASED EXECUTION DEMONSTRATION")
    print("=" * 60)
    print("Estimating execution prices from synthetic orderbook depth")
    print()
    
    # Generate synthetic depth for demonstration
    mid_price = 150.0
    depth = slippage_model.generate_synthetic_depth(
        mid_price=mid_price,
        spread_bps=20.0,  # 20 bps spread
        depth_levels=8,
        base_size=1000.0,
        token='ETH'
    )
    
    print(f"Mid Price: ${mid_price}")
    print(f"Bid-Ask Spread: 20 bps")
    print()
    
    # Show orderbook levels
    print("Orderbook Depth:")
    print(f"{'Bids':<20} {'Asks':<20}")
    print(f"{'Price':<8} {'Size':<8} {'Price':<8} {'Size':<8}")
    print("-" * 40)
    
    for i in range(min(5, len(depth['bids']))):
        bid_price, bid_size = depth['bids'][i]
        ask_price, ask_size = depth['asks'][i]
        print(f"{bid_price:<8.2f} {bid_size:<8.0f} {ask_price:<8.2f} {ask_size:<8.0f}")
    
    print()
    
    # Test different order sizes
    test_sizes_token = [100, 500, 2000]  # Token units
    
    print("Execution Analysis:")
    print(f"{'Size (tokens)':<15} {'Side':<6} {'Exec Price':<12} {'Slippage':<12} {'Basis Points':<12}")
    print("-" * 70)
    
    for size in test_sizes_token:
        # Test buy orders
        exec_price_buy, slippage_buy = slippage_model.estimate_execution_price_from_depth(
            size, depth, side='buy', current_price=mid_price
        )
        
        # Test sell orders  
        exec_price_sell, slippage_sell = slippage_model.estimate_execution_price_from_depth(
            size, depth, side='sell', current_price=mid_price
        )
        
        print(f"{size:<15} {'BUY':<6} ${exec_price_buy:<11.2f} {format_percentage(slippage_buy):<12} {format_bps(slippage_buy):<12}")
        print(f"{size:<15} {'SELL':<6} ${exec_price_sell:<11.2f} {format_percentage(slippage_sell):<12} {format_bps(slippage_sell):<12}")


def demo_token_specific_analysis():
    """Demonstrate token-specific slippage analysis"""
    print("\n" + "=" * 60)
    print("TOKEN-SPECIFIC SLIPPAGE ANALYSIS")
    print("=" * 60)
    print("Comparing slippage across different tokens")
    print()
    
    test_notional = 50_000  # $50k trade
    test_adv = 100_000_000  # $100M ADV
    
    tokens = ['SOL', 'ETH', 'BTC', 'USDC', 'USDT']
    
    print(f"Trade Size: ${test_notional:,}")
    print(f"Assumed ADV: ${test_adv:,}")
    print()
    print(f"{'Token':<8} {'Sqrt Model':<12} {'A-C Model':<12} {'Combined':<12}")
    print("-" * 50)
    
    for token in tokens:
        # Square-root model
        sqrt_slippage = slippage_model.estimate_slippage_by_notional(
            test_notional, test_adv, token=token
        )
        
        # Almgren-Chriss model
        ac_slippage = slippage_model.estimate_almgren_chriss_impact(
            test_notional, test_adv, token=token
        )
        
        # Combined estimate
        combined = slippage_model.estimate_combined_slippage(
            notional_usd=test_notional,
            token=token,
            adv_usd=test_adv
        )
        
        print(f"{token:<8} {format_bps(sqrt_slippage):<12} {format_bps(ac_slippage):<12} {format_bps(combined['recommended']):<12}")


def demo_size_impact_comparison():
    """Demonstrate how slippage scales with trade size"""
    print("\n" + "=" * 60)
    print("TRADE SIZE IMPACT COMPARISON")
    print("=" * 60)
    print("How slippage scales across different position sizes")
    print()
    
    # Standard test parameters
    adv_usd = 80_000_000  # $80M ADV
    token = 'SOL'
    
    # Test sizes: $1k to $1M
    test_sizes = [1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]
    
    print(f"Token: {token}")
    print(f"ADV: ${adv_usd:,}")
    print()
    print(f"{'Trade Size':<12} {'Participation':<15} {'Sqrt Model':<12} {'A-C Model':<12} {'Ratio (AC/Sqrt)':<15}")
    print("-" * 80)
    
    for notional in test_sizes:
        participation = notional / adv_usd
        
        sqrt_slippage = slippage_model.estimate_slippage_by_notional(
            notional, adv_usd, token=token
        )
        
        ac_slippage = slippage_model.estimate_almgren_chriss_impact(
            notional, adv_usd, token=token
        )
        
        ratio = ac_slippage / sqrt_slippage if sqrt_slippage > 0 else 0
        
        print(f"${notional:<10,} {participation:<15.4%} {format_bps(sqrt_slippage):<12} {format_bps(ac_slippage):<12} {ratio:<15.2f}")


def demo_realistic_scenarios():
    """Demonstrate realistic trading scenarios"""
    print("\n" + "=" * 60)
    print("REALISTIC TRADING SCENARIOS")
    print("=" * 60)
    print("Slippage estimates for real-world arbitrage situations")
    print()
    
    scenarios = [
        {
            'name': 'Small Arb (Retail)',
            'notional': 2_500,
            'token': 'SOL',
            'adv': 120_000_000,
            'description': '$2.5k SOL arbitrage'
        },
        {
            'name': 'Medium Arb (Fund)',
            'notional': 75_000,
            'token': 'ETH', 
            'adv': 800_000_000,
            'description': '$75k ETH arbitrage'
        },
        {
            'name': 'Large Arb (Institution)',
            'notional': 500_000,
            'token': 'BTC',
            'adv': 2_000_000_000,
            'description': '$500k BTC arbitrage'
        },
        {
            'name': 'Stablecoin Arb',
            'notional': 100_000,
            'token': 'USDC',
            'adv': 300_000_000,
            'description': '$100k USDC arbitrage'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}: {scenario['description']}")
        print(f"ADV: ${scenario['adv']:,}")
        print("-" * 40)
        
        # Generate synthetic depth
        mid_price = {'SOL': 180, 'ETH': 2500, 'BTC': 65000, 'USDC': 1.0}[scenario['token']]
        size_token = scenario['notional'] / mid_price
        
        depth = slippage_model.generate_synthetic_depth(
            mid_price, token=scenario['token']
        )
        
        # Combined analysis
        results = slippage_model.estimate_combined_slippage(
            notional_usd=scenario['notional'],
            token=scenario['token'],
            adv_usd=scenario['adv'],
            depth=depth,
            current_price=mid_price,
            side='buy'
        )
        
        print(f"Recommended Slippage: {format_bps(results['recommended'])}")
        
        if 'sqrt_model' in results:
            print(f"Square-root Model:    {format_bps(results['sqrt_model'])}")
        if 'almgren_chriss' in results:
            print(f"Almgren-Chriss:       {format_bps(results['almgren_chriss'])}")
        if 'depth_based' in results:
            print(f"Depth-based:          {format_bps(results['depth_based'])}")


def main():
    """Run all slippage model demonstrations"""
    print("CRYPTO ARBITRAGE PLATFORM")
    print("Slippage & Market Impact Model Demonstration")
    print(f"Configured with k={slippage_model.config.k_sqrt}, a={slippage_model.config.a_coeff}, b={slippage_model.config.b_power}")
    
    try:
        demo_square_root_model()
        demo_almgren_chriss_model()
        demo_depth_based_execution()
        demo_token_specific_analysis()
        demo_size_impact_comparison()
        demo_realistic_scenarios()
        
        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("The slippage model provides sophisticated market impact")
        print("estimation for cross-protocol arbitrage execution.")
        print("Use these estimates to optimize trade sizing and timing.")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()