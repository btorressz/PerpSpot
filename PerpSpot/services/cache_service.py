import json
import logging
import redis
import time
import random
from typing import Dict, Optional, Any
from functools import wraps
from threading import Lock
from decimal import Decimal
from cachetools import TTLCache

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 7, max_local_cache_size: int = 1000):
        """
        Initialize hybrid cache service with TTLCache + Redis fallback
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default time-to-live in seconds (7 seconds for balance between freshness and performance)
            max_local_cache_size: Maximum size of local TTL cache
        """
        self.default_ttl = default_ttl
        self.lock = Lock()
        
        # Initialize thread-safe TTL cache
        self.local_cache = TTLCache(maxsize=max_local_cache_size, ttl=default_ttl)
        
        # Attempt Redis connection as fallback
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connection established successfully")
            self.redis_connected = True
            
        except (redis.RedisError, ConnectionError) as e:
            logger.warning(f"Redis connection failed: {e}. Running with local cache only.")
            self.redis_client = None
            self.redis_connected = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (local TTL cache first, then Redis fallback)"""
        # Check local cache first (thread-safe)
        with self.lock:
            if key in self.local_cache:
                return self.local_cache[key]
        
        # Fallback to Redis if available
        if not self.redis_connected:
            return None
            
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_connected:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            json_value = json.dumps(value, default=str)  # Handle datetime serialization
            self.redis_client.setex(key, ttl, json_value)
            return True
        except (redis.RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.connected:
            return False
            
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.connected:
            return False
            
        try:
            return bool(self.redis_client.exists(key))
        except redis.RedisError as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False
    
    def flush_all(self) -> bool:
        """Clear all cache entries"""
        if not self.connected:
            return False
            
        try:
            self.redis_client.flushdb()
            logger.info("Cache flushed successfully")
            return True
        except redis.RedisError as e:
            logger.error(f"Cache flush error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.connected:
            return {"connected": False}
            
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get('used_memory_human', 'N/A'),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)) * 100
            }
        except redis.RedisError as e:
            logger.warning(f"Cache stats error: {e}")
            return {"connected": False, "error": str(e)}
    
    def get_cached_data(self, key: str, default=None) -> Any:
        """Unified method to get cached data with fallback default"""
        result = self.get(key)
        return result if result is not None else default
    
    def set_cached_data(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Unified method to set cached data"""
        return self.set(key, data, ttl)
    
    @property 
    def connected(self) -> bool:
        """Check if cache service is connected (for backward compatibility)"""
        return self.redis_connected


def with_exponential_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True):
    """
    Decorator that adds exponential backoff with jitter to function calls
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
        max_delay: Maximum delay in seconds
        jitter: Add random jitter to prevent thundering herd
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


def with_cache(cache_service: CacheService, key_prefix: str, ttl: Optional[int] = None):
    """
    Decorator that adds caching to function calls
    
    Args:
        cache_service: CacheService instance
        key_prefix: Prefix for cache keys
        ttl: Time-to-live in seconds (uses cache_service default if None)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache first
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Cache miss - call the function
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            
            # Store result in cache
            if result is not None:
                cache_service.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache service instance
cache_service = CacheService()