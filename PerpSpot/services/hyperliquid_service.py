import logging
import os
from typing import Dict, Optional, List
import time
import requests
from hyperliquid.info import Info
from hyperliquid.utils import constants

logger = logging.getLogger(__name__)

class HyperliquidService:
    def __init__(self):
        self.testnet = os.getenv('HYPERLIQUID_TESTNET', 'true').lower() == 'true'
        self.base_url = constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
        
        # Use Redis cache service
        from .cache_service import cache_service
        self.cache = cache_service
        self._cache_timeout = 3  # seconds - faster updates for perpetuals
        
        # Initialize with fallback tokens first - include stablecoins
        self.supported_tokens = ['SOL', 'ETH', 'BTC', 'APT', 'ATOM', 'MATIC', 'BNB', 'AVAX', 'USDC', 'USDT']
        self._token_universe = {}
        
        # WebSocket integration
        self.ws_listener = None
        self.ws_enabled = False
        self.ws_data = {}  # Cache for WebSocket data
        
        # Initialize without calling any APIs to avoid startup failures
        self.info = None
        try:
            # Lazy initialization - will be created when first needed
            pass
        except Exception as e:
            logger.warning(f"Failed to initialize Hyperliquid service: {str(e)}. Using fallback tokens.")
        
    def _ensure_info_client(self):
        """Lazy initialization of Hyperliquid Info client"""
        if self.info is None:
            try:
                self.info = Info(self.base_url, skip_ws=True)
            except Exception as e:
                logger.error(f"Failed to create Hyperliquid Info client: {str(e)}")
                raise
        return self.info
        
    def _update_supported_tokens(self):
        """Update supported tokens list from Hyperliquid universe"""
        try:
            info_client = self._ensure_info_client()
            metas = info_client.meta()
            universe = metas.get('universe', [])
            
            self.supported_tokens = []
            self._token_universe = {}
            
            for asset in universe:
                name = asset.get('name', '')
                if name:
                    # Clean up token name - remove common suffixes
                    clean_name = name.replace('-PERP', '').replace('-USD', '').upper()
                    self.supported_tokens.append(clean_name)
                    self._token_universe[clean_name] = asset
                    
            logger.info(f"Updated Hyperliquid supported tokens: {self.supported_tokens[:10]}...")  # Log first 10
            
        except Exception as e:
            logger.error(f"Error updating supported tokens: {str(e)}")
            # Fallback to common tokens
            self.supported_tokens = ['SOL', 'ETH', 'BTC', 'JUP', 'BONK', 'ORCA']
        
    def get_perpetual_prices(self) -> Dict[str, Dict]:
        """Get perpetual futures prices for supported tokens"""
        try:
            # Check Redis cache first
            cache_key = 'hyperliquid:perpetual_prices'
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Try to initialize client if needed
            try:
                info_client = self._ensure_info_client()
            except Exception as e:
                logger.error(f"Cannot connect to Hyperliquid: {str(e)}")
                return {}
            
            # Get all metas (market information)
            metas = info_client.meta()
            universe = metas.get('universe', [])
            
            # Get all mid prices
            all_mids = info_client.all_mids()
            
            # Skip token refresh to reduce API calls and memory usage
            # self._update_supported_tokens()
            
            prices = {}
            for token in self.supported_tokens:
                try:
                    # Use cached token info from universe
                    token_info = self._token_universe.get(token)
                    if not token_info:
                        continue
                    
                    # Find price for this token in all_mids
                    token_price = None
                    original_name = token_info.get('name', token)  # Use original Hyperliquid name
                    
                    if all_mids and isinstance(all_mids, list):
                        # Try different name variations
                        for mid_data in all_mids:
                            if isinstance(mid_data, dict):
                                coin_name = mid_data.get('coin', '').upper()
                                if (coin_name == token.upper() or 
                                    coin_name == original_name.upper() or
                                    coin_name.replace('-PERP', '').replace('-USD', '') == token.upper()):
                                    token_price = float(mid_data.get('px', 0))
                                    break
                    elif all_mids and isinstance(all_mids, dict):
                        # Handle case where all_mids is a dict instead of list
                        for name_variant in [token.upper(), token, original_name.upper(), original_name]:
                            if name_variant in all_mids:
                                price_data = all_mids.get(name_variant)
                                if isinstance(price_data, (int, float, str)):
                                    token_price = float(price_data)
                                    break
                                elif isinstance(price_data, dict):
                                    token_price = float(price_data.get('px', 0) or price_data.get('price', 0))
                                    if token_price > 0:
                                        break
                    
                    if token_price and token_price > 0:
                        # Get funding rate
                        funding_rate = self._get_funding_rate(token)
                        
                        # Get index price (for now, use mark price as approximation)
                        index_price = token_price  # In production, fetch actual index price
                        
                        prices[token] = {
                            'mark_price': token_price,
                            'index_price': index_price,
                            'funding_rate': funding_rate,
                            'spread_pct': ((token_price - index_price) / index_price * 100) if index_price else 0,
                            'timestamp': int(time.time() * 1000)
                        }
                        
                except Exception as e:
                    logger.error(f"Error getting price for {token}: {str(e)}")
                    continue
            
            # Cache the result in Redis
            if prices:
                self.cache.set(cache_key, prices, ttl=self._cache_timeout)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid prices: {str(e)}")
            return {}
    
    def _get_funding_rate(self, token: str) -> float:
        """Get funding rate for a token"""
        try:
            # Use meta endpoint to get funding info
            info_client = self._ensure_info_client()
            meta = info_client.meta()
            universe = meta.get('universe', [])
            
            for asset in universe:
                if asset.get('name', '').upper() == token.upper():
                    funding = asset.get('funding', {})
                    return float(funding.get('funding', 0))
            
            return 0.0
        except Exception as e:
            logger.error(f"Error getting funding rate for {token}: {str(e)}")
            return 0.0
    
    def get_all_mids(self) -> List[Dict]:
        """Get all mid prices"""
        try:
            info_client = self._ensure_info_client()
            return info_client.all_mids()
        except Exception as e:
            logger.error(f"Error getting all mids: {str(e)}")
            return []
    
    def get_mark_price(self, token: str) -> Optional[float]:
        """Get mark price for a specific token"""
        try:
            all_mids = self.get_all_mids()
            if all_mids and isinstance(all_mids, list):
                for mid_data in all_mids:
                    if isinstance(mid_data, dict) and mid_data.get('coin', '').upper() == token.upper():
                        return float(mid_data.get('px', 0))
            elif all_mids and isinstance(all_mids, dict):
                if token.upper() in all_mids or token in all_mids:
                    price_data = all_mids.get(token.upper()) or all_mids.get(token)
                    if isinstance(price_data, (int, float, str)):
                        return float(price_data)
                    elif isinstance(price_data, dict):
                        return float(price_data.get('px', 0) or price_data.get('price', 0))
            return None
        except Exception as e:
            logger.error(f"Error getting mark price for {token}: {str(e)}")
            return None
    
    def get_funding_rates(self) -> Dict[str, Dict]:
        """Get funding rates for all supported tokens"""
        try:
            info_client = self._ensure_info_client()
            meta = info_client.meta()
            universe = meta.get('universe', [])
            
            funding_rates = {}
            for token in self.supported_tokens:
                for asset in universe:
                    if asset.get('name', '').upper() == token.upper():
                        funding = asset.get('funding', {})
                        funding_rates[token] = {
                            'current_funding_rate': float(funding.get('funding', 0)),
                            'predicted_funding_rate': float(funding.get('predictedFunding', 0))
                        }
                        break
            
            return funding_rates
        except Exception as e:
            logger.error(f"Error getting funding rates: {str(e)}")
            return {}
    
    def simulate_position(self, token: str, side: str, size: float, leverage: int = 1) -> Dict:
        """Simulate opening a perpetual position"""
        try:
            prices = self.get_perpetual_prices()
            if token not in prices:
                return {'error': f'Token {token} not found'}
            
            mark_price = prices[token]['mark_price']
            funding_rate = prices[token]['funding_rate']
            
            # Calculate position details
            notional_value = size * mark_price
            margin_required = notional_value / leverage
            
            # Estimate liquidation price (simplified)
            if side.lower() == 'long':
                liquidation_price = mark_price * (1 - 0.9 / leverage)
            else:
                liquidation_price = mark_price * (1 + 0.9 / leverage)
            
            return {
                'token': token,
                'side': side,
                'size': size,
                'leverage': leverage,
                'entry_price': mark_price,
                'notional_value': notional_value,
                'margin_required': margin_required,
                'liquidation_price': liquidation_price,
                'funding_rate': funding_rate,
                'estimated_fees': notional_value * 0.0002,  # Approximate trading fee
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error simulating position: {str(e)}")
            return {'error': str(e)}
    
    def health_check(self) -> bool:
        """Check if Hyperliquid API is responding"""
        try:
            info_client = self._ensure_info_client()
            meta = info_client.meta()
            return bool(meta and 'universe' in meta)
        except Exception as e:
            logger.error(f"Hyperliquid health check failed: {str(e)}")
            return False
    
    def get_market_stats(self) -> Dict:
        """Get overall market statistics"""
        try:
            info_client = self._ensure_info_client()
            metas = info_client.meta()
            universe = metas.get('universe', [])
            
            total_volume_24h = 0
            active_markets = len(universe)
            
            return {
                'active_markets': active_markets,
                'total_volume_24h': total_volume_24h,
                'supported_tokens': len(self.supported_tokens),
                'network': 'testnet' if self.testnet else 'mainnet'
            }
            
        except Exception as e:
            logger.error(f"Error getting market stats: {str(e)}")
            return {}
    
    def enable_websocket_streaming(self):
        """Enable real-time WebSocket data streaming with mainnet/testnet fallback"""
        try:
            if self.ws_listener is None:
                from .ws_listener import WebSocketListener
                self.ws_listener = WebSocketListener(price_store=self)
                
                # Add callback to handle incoming WebSocket data
                self.ws_listener.add_callback(self._handle_ws_data)
                
                # Start WebSocket using the background listener method
                self.ws_listener.start_background_listener()
                
                self.ws_enabled = True
                logger.info("WebSocket streaming enabled with mainnet/testnet fallback")
                
        except Exception as e:
            logger.error(f"Failed to enable WebSocket streaming: {str(e)}")
            self.ws_enabled = False
    
    def _handle_ws_data(self, data_type: str, data: dict):
        """Handle incoming WebSocket data"""
        try:
            if data_type == "prices":
                # Update cached WebSocket price data
                self.ws_data.update(data)
                
                # Update cache with fresh data
                cache_key = 'hyperliquid:ws_prices'
                self.cache.set(cache_key, data, ttl=1)  # Very short TTL for real-time data
                
                logger.debug(f"Updated WebSocket price data for {len(data)} tokens")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket data: {str(e)}")
    
    def get_websocket_prices(self) -> Dict[str, Dict]:
        """Get real-time prices from WebSocket if available, fallback to REST API"""
        try:
            if self.ws_enabled and self.ws_data:
                logger.debug("Using real-time WebSocket price data")
                return self.ws_data
            else:
                # Fallback to REST API method
                logger.debug("WebSocket not available, using REST API")
                return self.get_perpetual_prices()
                
        except Exception as e:
            logger.error(f"Error getting WebSocket prices: {str(e)}")
            return self.get_perpetual_prices()
