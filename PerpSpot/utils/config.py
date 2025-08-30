import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration class for the arbitrage platform"""
    
    # Flask settings
    SECRET_KEY: str = os.getenv('SESSION_SECRET', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    HOST: str = '0.0.0.0'
    PORT: int = 5000
    
    # Hyperliquid settings
    HYPERLIQUID_TESTNET: bool = os.getenv('HYPERLIQUID_TESTNET', 'true').lower() == 'true'
    HYPERLIQUID_API_KEY: Optional[str] = os.getenv('HYPERLIQUID_API_KEY')
    HYPERLIQUID_SECRET_KEY: Optional[str] = os.getenv('HYPERLIQUID_SECRET_KEY')
    
    # Jupiter settings
    JUPITER_API_KEY: Optional[str] = os.getenv('JUPITER_API_KEY')
    
    # API settings
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '10'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY: float = float(os.getenv('RETRY_DELAY', '1.0'))
    
    # Trading settings
    MIN_SPREAD_THRESHOLD: float = float(os.getenv('MIN_SPREAD_THRESHOLD', '0.5'))
    DEFAULT_NOTIONAL: float = float(os.getenv('DEFAULT_NOTIONAL', '1000.0'))
    MAX_POSITION_SIZE: float = float(os.getenv('MAX_POSITION_SIZE', '10000.0'))
    
    # Data settings
    UPDATE_INTERVAL: int = int(os.getenv('UPDATE_INTERVAL', '10'))  # seconds
    HISTORICAL_DATA_POINTS: int = int(os.getenv('HISTORICAL_DATA_POINTS', '1000'))
    CHART_DATA_POINTS: int = int(os.getenv('CHART_DATA_POINTS', '50'))
    
    # Supported tokens
    SUPPORTED_TOKENS: list = [
        'SOL', 'ETH', 'BTC', 'USDC', 'USDT', 'JUP', 'BONK', 'ORCA', 'HL'
    ]
    
    # Fallback API settings
    COINGECKO_API_KEY: Optional[str] = os.getenv('COINGECKO_API_KEY')
    KRAKEN_API_KEY: Optional[str] = os.getenv('KRAKEN_API_KEY')
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.MIN_SPREAD_THRESHOLD < 0:
            self.MIN_SPREAD_THRESHOLD = 0.1
            
        if self.UPDATE_INTERVAL < 5:
            self.UPDATE_INTERVAL = 5  # Minimum 5 seconds
            
        if self.DEFAULT_NOTIONAL <= 0:
            self.DEFAULT_NOTIONAL = 100.0

# Global config instance
config = Config()
