import redis
import json
import time
import logging
import asyncio
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Configuration for Redis caching"""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    default_ttl: int = 5  # seconds
    max_retries: int = 3
    retry_backoff_base: float = 0.5
    retry_backoff_max: float = 30.0

class RedisPriceCache:
    """Redis-backed caching layer for price polling endpoints"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client = None
        self.connected = False
        self.retry_attempts = {}
        
        try:
            self.redis_client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                decode_responses=True,
                socket_timeout=5,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            self.connected = True
            logger.info("Connected to Redis cache")
            
        except Exception as e:
            logger.warning(f"Redis connection failed, running without cache: {e}")
            self.connected = False
    
    def _get_cache_key(self, service: str, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for service endpoint"""
        key_parts = [f"price_cache:{service}:{endpoint}"]
        
        if params:
            # Sort params for consistent keys
            sorted_params = sorted(params.items())
            param_str = ":".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(param_str)
            
        return ":".join(key_parts)
    
    def get_cached_data(self, service: str, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Retrieve cached data"""
        if not self.connected:
            return None
            
        try:
            cache_key = self._get_cache_key(service, endpoint, params)
            cached_value = self.redis_client.get(cache_key)
            
            if cached_value:
                data = json.loads(cached_value)
                logger.debug(f"Cache hit for {cache_key}")
                return data
                
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            
        return None
    
    def cache_data(self, service: str, endpoint: str, data: Dict, params: Dict = None, ttl: int = None) -> bool:
        """Cache data with TTL"""
        if not self.connected:
            return False
            
        try:
            cache_key = self._get_cache_key(service, endpoint, params)
            ttl = ttl or self.config.default_ttl
            
            # Add timestamp to cached data
            cached_data = {
                'data': data,
                'cached_at': int(time.time() * 1000),
                'ttl': ttl
            }
            
            success = self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cached_data)
            )
            
            if success:
                logger.debug(f"Cached data for {cache_key} (TTL: {ttl}s)")
                return True
                
        except Exception as e:
            logger.error(f"Error caching data: {e}")
            
        return False
    
    def invalidate_cache(self, service: str, endpoint: str = None, params: Dict = None):
        """Invalidate cached data"""
        if not self.connected:
            return
            
        try:
            if endpoint:
                cache_key = self._get_cache_key(service, endpoint, params)
                self.redis_client.delete(cache_key)
                logger.debug(f"Invalidated cache key: {cache_key}")
            else:
                # Invalidate all keys for service
                pattern = f"price_cache:{service}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
                    logger.debug(f"Invalidated {len(keys)} cache keys for service {service}")
                    
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.connected:
            return {'connected': False}
            
        try:
            info = self.redis_client.info()
            return {
                'connected': True,
                'used_memory': info.get('used_memory_human', 'N/A'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'connected': False, 'error': str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

class BackoffRetryManager:
    """Manage backoff retry logic for failed API calls"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.retry_state = {}
    
    def should_retry(self, service: str) -> bool:
        """Check if service should be retried based on backoff"""
        if service not in self.retry_state:
            return True
            
        state = self.retry_state[service]
        current_time = time.time()
        
        if current_time >= state['next_retry_time']:
            return True
            
        return False
    
    def record_failure(self, service: str):
        """Record a failure and update retry state"""
        current_time = time.time()
        
        if service not in self.retry_state:
            self.retry_state[service] = {
                'failures': 0,
                'first_failure': current_time,
                'last_failure': current_time,
                'next_retry_time': current_time
            }
        
        state = self.retry_state[service]
        state['failures'] += 1
        state['last_failure'] = current_time
        
        # Calculate backoff delay
        delay = min(
            self.config.retry_backoff_base * (2 ** (state['failures'] - 1)),
            self.config.retry_backoff_max
        )
        
        state['next_retry_time'] = current_time + delay
        
        logger.debug(f"Service {service} failure #{state['failures']}, next retry in {delay:.1f}s")
    
    def record_success(self, service: str):
        """Record a success and reset retry state"""
        if service in self.retry_state:
            del self.retry_state[service]
            logger.debug(f"Service {service} recovered, retry state cleared")
    
    def get_retry_stats(self) -> Dict:
        """Get retry statistics"""
        current_time = time.time()
        stats = {}
        
        for service, state in self.retry_state.items():
            next_retry_in = max(0, state['next_retry_time'] - current_time)
            stats[service] = {
                'failures': state['failures'],
                'next_retry_in_seconds': next_retry_in,
                'failing_since': state['first_failure']
            }
            
        return stats

class EnhancedPriceFetcher:
    """Enhanced price fetcher with Redis caching and retry logic"""
    
    def __init__(self, cache_config: CacheConfig = None):
        self.cache = RedisPriceCache(cache_config)
        self.retry_manager = BackoffRetryManager(cache_config or CacheConfig())
        self.request_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'api_failures': 0
        }
    
    async def fetch_with_cache(self,
                             service: str,
                             endpoint: str,
                             fetch_function: Callable,
                             params: Dict = None,
                             ttl: int = None,
                             force_refresh: bool = False) -> Optional[Dict]:
        """
        Fetch data with caching and retry logic
        
        Args:
            service: Service name (e.g., 'jupiter', 'coingecko')
            endpoint: Endpoint name (e.g., 'prices', 'quote')
            fetch_function: Async function to fetch data from API
            params: Parameters for the fetch function
            ttl: Cache TTL override
            force_refresh: Force API call and cache refresh
        """
        params = params or {}
        
        # Try cache first (unless force refresh)
        if not force_refresh:
            cached_data = self.cache.get_cached_data(service, endpoint, params)
            if cached_data:
                self.request_stats['cache_hits'] += 1
                return cached_data['data']
        
        self.request_stats['cache_misses'] += 1
        
        # Check if service is in backoff
        if not self.retry_manager.should_retry(service):
            logger.debug(f"Service {service} is in backoff, skipping API call")
            return None
        
        # Make API call
        try:
            logger.debug(f"Making API call to {service}/{endpoint}")
            data = await fetch_function(**params)
            
            if data:
                # Cache successful response
                self.cache.cache_data(service, endpoint, data, params, ttl)
                self.retry_manager.record_success(service)
                self.request_stats['api_calls'] += 1
                return data
            else:
                self.retry_manager.record_failure(service)
                self.request_stats['api_failures'] += 1
                return None
                
        except Exception as e:
            logger.error(f"API call failed for {service}/{endpoint}: {e}")
            self.retry_manager.record_failure(service)
            self.request_stats['api_failures'] += 1
            return None
    
    def invalidate_service_cache(self, service: str):
        """Invalidate all cached data for a service"""
        self.cache.invalidate_cache(service)
    
    def get_stats(self) -> Dict:
        """Get comprehensive fetcher statistics"""
        cache_stats = self.cache.get_cache_stats()
        retry_stats = self.retry_manager.get_retry_stats()
        
        total_requests = self.request_stats['cache_hits'] + self.request_stats['cache_misses']
        cache_hit_rate = (self.request_stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_stats': cache_stats,
            'retry_stats': retry_stats,
            'request_stats': {
                **self.request_stats,
                'cache_hit_rate_pct': cache_hit_rate,
                'total_requests': total_requests
            }
        }

# Global price fetcher instance
price_fetcher = EnhancedPriceFetcher()

# Convenience functions for different services
async def fetch_jupiter_prices(tokens: List[str], ttl: int = 5) -> Optional[Dict]:
    """Fetch Jupiter prices with caching"""
    
    async def _fetch_jupiter():
        # Import here to avoid circular imports
        from .jupiter_service import JupiterService
        service = JupiterService()
        return service.get_spot_prices()
    
    return await price_fetcher.fetch_with_cache(
        service='jupiter',
        endpoint='prices',
        fetch_function=_fetch_jupiter,
        params={'tokens': tokens},
        ttl=ttl
    )

async def fetch_coingecko_prices(tokens: List[str], ttl: int = 10) -> Optional[Dict]:
    """Fetch CoinGecko prices with caching"""
    
    async def _fetch_coingecko():
        from .fallback_service import FallbackService
        service = FallbackService()
        return service.get_coingecko_prices(tokens)
    
    return await price_fetcher.fetch_with_cache(
        service='coingecko',
        endpoint='prices',
        fetch_function=_fetch_coingecko,
        params={'tokens': tokens},
        ttl=ttl
    )

async def fetch_hyperliquid_prices(ttl: int = 3) -> Optional[Dict]:
    """Fetch Hyperliquid prices with caching"""
    
    async def _fetch_hyperliquid():
        from .hyperliquid_service import HyperliquidService
        service = HyperliquidService()
        return service.get_perpetual_prices()
    
    return await price_fetcher.fetch_with_cache(
        service='hyperliquid',
        endpoint='prices',
        fetch_function=_fetch_hyperliquid,
        ttl=ttl
    )

def get_price_fetcher_stats() -> Dict:
    """Get price fetcher statistics"""
    return price_fetcher.get_stats()

def invalidate_all_price_caches():
    """Invalidate all price caches"""
    for service in ['jupiter', 'coingecko', 'hyperliquid', 'kraken']:
        price_fetcher.invalidate_service_cache(service)