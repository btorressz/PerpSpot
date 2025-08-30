import logging
import requests
import time
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class JupiterService:
    def __init__(self):
        self.base_url = "https://quote-api.jup.ag/v6"
        self.price_url = "https://price.jup.ag/v4/price"
        self.token_list_url = "https://token.jup.ag/all"
        
        # Token mint addresses for supported tokens
        self.token_mints = {
            'SOL': 'So11111111111111111111111111111111111111112',
            'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
            'JUP': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'ORCA': 'orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE',
            'HL': '4Ae83YgsBcwJTMx3am3gi5Ppnp1KwmunznWAoYeqgDgL'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoArbitrageBot/1.0',
            'Accept': 'application/json'
        })
        
        # Use Redis cache service
        from .cache_service import cache_service
        self.cache = cache_service
        self._cache_timeout = 5  # seconds
        
    def get_spot_prices(self, use_fallback=True) -> Dict[str, Dict]:
        """Get spot prices for supported tokens"""
        # Check Redis cache first
        cache_key = 'jupiter:spot_prices'
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        prices = {}
        
        for token, mint_address in self.token_mints.items():
            try:
                price_data = self._get_token_price(mint_address)
                if price_data:
                    prices[token] = {
                        'spot_price': price_data['price'],
                        'price': price_data['price'],  # Also include 'price' key for consistency
                        'mint_address': mint_address,
                        'liquidity': price_data.get('liquidity', 0),
                        'volume_24h': price_data.get('volume24h', 0),
                        'volume24h': price_data.get('volume24h', 0),  # Both variants for consistency
                        'timestamp': int(time.time() * 1000)
                    }
            except Exception as e:
                logger.error(f"Error getting Jupiter price for {token}: {str(e)}")
                continue
        
        # If we don't have many prices and fallback is enabled, don't cache yet
        if len(prices) < len(self.token_mints) // 2 and use_fallback:
            # Don't cache incomplete results when we expect fallback to help
            return prices
        
        # Cache the result in Redis
        if prices:
            self.cache.set(cache_key, prices, ttl=self._cache_timeout)
        
        return prices
    
    def get_multiple_token_prices(self, tokens: List[str], base_currency: str = 'USDC') -> Dict[str, float]:
        """Get prices for multiple tokens"""
        try:
            prices = {}
            all_prices = self.get_spot_prices()
            
            for token in tokens:
                if token in all_prices:
                    prices[token] = all_prices[token]['spot_price']
                else:
                    logger.warning(f"Price not found for token: {token}")
            
            return prices
        except Exception as e:
            logger.error(f"Error getting multiple token prices: {str(e)}")
            return {}
    
    def _get_token_price(self, mint_address: str) -> Optional[Dict]:
        """Get price for a specific token by mint address"""
        try:
            response = self.session.get(
                f"{self.price_url}",
                params={'ids': mint_address},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and mint_address in data['data']:
                    token_data = data['data'][mint_address]
                    return {
                        'price': float(token_data.get('price', 0)),
                        'liquidity': float(token_data.get('liquidity', 0)),
                        'volume24h': float(token_data.get('volume24h', 0))
                    }
            else:
                logger.warning(f"Jupiter API returned status {response.status_code} for {mint_address}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting price for {mint_address}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting price for {mint_address}: {str(e)}")
            
        return None
    
    def get_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50) -> Optional[Dict]:
        """Get a quote for swapping tokens"""
        try:
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': str(amount),
                'slippageBps': str(slippage_bps)
            }
            
            response = self.session.get(
                f"{self.base_url}/quote",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Jupiter quote API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error getting quote: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting quote: {str(e)}")
            
        return None
    
    def simulate_swap(self, from_token: str, to_token: str, amount: float) -> Dict:
        """Simulate a token swap"""
        try:
            if from_token not in self.token_mints or to_token not in self.token_mints:
                return {'error': 'Unsupported token pair'}
            
            input_mint = self.token_mints[from_token]
            output_mint = self.token_mints[to_token]
            
            # Convert amount to smallest units (assuming 6 decimals for most tokens, 9 for SOL)
            decimals = 9 if from_token == 'SOL' else 6
            amount_units = int(amount * (10 ** decimals))
            
            quote = self.get_quote(input_mint, output_mint, amount_units)
            
            if quote:
                output_amount = float(quote.get('outAmount', 0)) / (10 ** (9 if to_token == 'SOL' else 6))
                price_impact = float(quote.get('priceImpactPct', 0))
                
                return {
                    'from_token': from_token,
                    'to_token': to_token,
                    'input_amount': amount,
                    'output_amount': output_amount,
                    'price_impact': price_impact,
                    'route': quote.get('routePlan', []),
                    'estimated_fees': self._calculate_fees(amount, price_impact),
                    'timestamp': int(time.time() * 1000)
                }
            else:
                return {'error': 'Failed to get quote from Jupiter'}
                
        except Exception as e:
            logger.error(f"Error simulating swap: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_fees(self, amount: float, price_impact: float) -> float:
        """Calculate estimated fees for a swap"""
        # Jupiter typically charges 0.1-0.5% in fees depending on the route
        base_fee = amount * 0.003  # 0.3% average
        impact_fee = amount * (price_impact / 100)
        return base_fee + impact_fee
    
    def get_route_map(self) -> Dict:
        """Get available trading routes"""
        try:
            response = self.session.get(
                f"{self.base_url}/indexed-route-map",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Jupiter route map API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting route map: {str(e)}")
            
        return {}
    
    def health_check(self) -> bool:
        """Check if Jupiter API is responding"""
        try:
            # Try to get a simple price quote
            response = self.session.get(
                f"{self.price_url}?ids={self.token_mints['SOL']}",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Jupiter health check failed: {str(e)}")
            return False
    
    def get_supported_tokens(self) -> List[str]:
        """Get list of supported tokens"""
        return list(self.token_mints.keys())
