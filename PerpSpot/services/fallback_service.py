import logging
import requests
import time
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class FallbackService:
    def __init__(self):
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        self.kraken_url = "https://api.kraken.com/0/public"
        
        # CoinGecko token IDs
        self.coingecko_ids = {
            'SOL': 'solana',
            'ETH': 'ethereum',
            'BTC': 'bitcoin',
            'USDC': 'usd-coin',
            'USDT': 'tether',
            'JUP': 'jupiter-exchange-solana',
            'BONK': 'bonk',
            'ORCA': 'orca',
            'HL': 'hyperliquid'
        }
        
        # Kraken trading pairs
        self.kraken_pairs = {
            'SOL': 'SOLUSD',
            'ETH': 'ETHUSD',
            'BTC': 'BTCUSD',
            'USDC': 'USDCUSD',
            'USDT': 'USDTUSD'
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CryptoArbitrageBot/1.0'
        })
        
        # Use Redis cache service
        from .cache_service import cache_service
        self.cache = cache_service
        
    def get_coingecko_prices(self, tokens: list) -> Dict[str, Dict]:
        """Get prices from CoinGecko API"""
        # Check Redis cache first
        cache_key = f"coingecko:prices:{hash(str(sorted(tokens)))}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
        
        prices = {}
        
        try:
            # Filter tokens that have CoinGecko IDs
            valid_tokens = [token for token in tokens if token in self.coingecko_ids]
            if not valid_tokens:
                return prices
            
            # Build CoinGecko IDs string
            ids = ','.join([self.coingecko_ids[token] for token in valid_tokens])
            
            response = self.session.get(
                f"{self.coingecko_url}/simple/price",
                params={
                    'ids': ids,
                    'vs_currencies': 'usd',
                    'include_market_cap': 'true',
                    'include_24hr_vol': 'true',
                    'include_24hr_change': 'true'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for token in valid_tokens:
                    cg_id = self.coingecko_ids[token]
                    if cg_id in data:
                        token_data = data[cg_id]
                        prices[token] = {
                            'price': float(token_data.get('usd', 0)),
                            'market_cap': float(token_data.get('usd_market_cap', 0)),
                            'volume_24h': float(token_data.get('usd_24h_vol', 0)),
                            'change_24h': float(token_data.get('usd_24h_change', 0)),
                            'source': 'coingecko',
                            'timestamp': int(time.time() * 1000)
                        }
            else:
                logger.warning(f"CoinGecko API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching CoinGecko prices: {str(e)}")
        
        # Cache successful results
        if prices:
            self.cache.set(cache_key, prices, ttl=10)  # 10-second TTL for CoinGecko
            
        return prices
    
    def get_multiple_coingecko_prices(self, tokens: List[str], vs_currency: str = 'usd') -> Dict[str, float]:
        """Get multiple token prices from CoinGecko"""
        try:
            prices_data = self.get_coingecko_prices(tokens)
            prices = {}
            
            for token, data in prices_data.items():
                if 'price' in data and data['price'] > 0:
                    prices[token] = data['price']
            
            return prices
        except Exception as e:
            logger.error(f"Error getting multiple CoinGecko prices: {str(e)}")
            return {}
    
    def get_kraken_prices(self, tokens: list) -> Dict[str, Dict]:
        """Get prices from Kraken API"""
        prices = {}
        
        try:
            # Filter tokens that have Kraken pairs
            valid_tokens = [token for token in tokens if token in self.kraken_pairs]
            if not valid_tokens:
                return prices
            
            # Build pairs string
            pairs = ','.join([self.kraken_pairs[token] for token in valid_tokens])
            
            response = self.session.get(
                f"{self.kraken_url}/Ticker",
                params={'pair': pairs},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('error'):
                    logger.error(f"Kraken API error: {data['error']}")
                    return prices
                
                result = data.get('result', {})
                
                for token in valid_tokens:
                    kraken_pair = self.kraken_pairs[token]
                    
                    # Kraken sometimes returns different pair formats
                    pair_data = None
                    for key in result.keys():
                        if kraken_pair.lower() in key.lower():
                            pair_data = result[key]
                            break
                    
                    if pair_data:
                        # Kraken returns price as [price, whole_lot_volume]
                        last_price = float(pair_data['c'][0])
                        volume_24h = float(pair_data['v'][1])  # 24h volume
                        
                        prices[token] = {
                            'price': last_price,
                            'volume_24h': volume_24h,
                            'bid': float(pair_data['b'][0]),
                            'ask': float(pair_data['a'][0]),
                            'source': 'kraken',
                            'timestamp': int(time.time() * 1000)
                        }
            else:
                logger.warning(f"Kraken API returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching Kraken prices: {str(e)}")
            
        return prices
    
    def get_multiple_kraken_prices(self, tokens: List[str], vs_currency: str = 'USD') -> Dict[str, float]:
        """Get multiple token prices from Kraken"""
        try:
            prices_data = self.get_kraken_prices(tokens)
            prices = {}
            
            for token, data in prices_data.items():
                if 'price' in data and data['price'] > 0:
                    prices[token] = data['price']
            
            return prices
        except Exception as e:
            logger.error(f"Error getting multiple Kraken prices: {str(e)}")
            return {}
    
    def get_fallback_prices(self, tokens: list) -> Dict[str, Dict]:
        """Get prices from fallback sources, trying CoinGecko first, then Kraken"""
        # Try CoinGecko first
        prices = self.get_coingecko_prices(tokens)
        
        # For tokens not found in CoinGecko, try Kraken
        missing_tokens = [token for token in tokens if token not in prices]
        if missing_tokens:
            kraken_prices = self.get_kraken_prices(missing_tokens)
            prices.update(kraken_prices)
        
        return prices
    
    def get_price_with_retry(self, token: str, max_retries: int = 3) -> Optional[Dict]:
        """Get price for a single token with retry logic"""
        for attempt in range(max_retries):
            try:
                # Try CoinGecko first
                cg_prices = self.get_coingecko_prices([token])
                if token in cg_prices:
                    return cg_prices[token]
                
                # Fall back to Kraken
                kraken_prices = self.get_kraken_prices([token])
                if token in kraken_prices:
                    return kraken_prices[token]
                
                # Wait before retry
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {token}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    
        return None
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of fallback services"""
        health = {}
        
        # Check CoinGecko
        try:
            response = self.session.get(
                f"{self.coingecko_url}/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=5
            )
            health['coingecko'] = response.status_code == 200
        except Exception as e:
            logger.error(f"CoinGecko health check failed: {str(e)}")
            health['coingecko'] = False
        
        # Check Kraken
        try:
            response = self.session.get(
                f"{self.kraken_url}/Time",
                timeout=5
            )
            health['kraken'] = response.status_code == 200
        except Exception as e:
            logger.error(f"Kraken health check failed: {str(e)}")
            health['kraken'] = False
        
        return health
