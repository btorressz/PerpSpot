"""
Generic WebSocket listener with reconnection logic for real-time data feeds.
"""

import asyncio
import json
import logging
import time
import websockets
from typing import Dict, Any, Callable, Optional
from threading import Thread, Event
import signal


logger = logging.getLogger(__name__)


class WebSocketListener:
    """Real-time WebSocket listener for Hyperliquid live data"""
    
    def __init__(self, price_store: Optional[object] = None):
        # WebSocket URLs with mainnet as primary, testnet as fallback
        self.mainnet_ws_url = "wss://api.hyperliquid.xyz/ws"
        self.testnet_ws_url = "wss://api.hyperliquid-testnet.xyz/ws"
        self.ws_url = self.mainnet_ws_url  # Start with mainnet
        self.use_testnet_fallback = False
        
        self.price_store = price_store
        self.connection = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_delay = 1
        self.max_delay = 60
        self.subscriptions = []
        self.data_callbacks = []
        
        # Tracked data
        self.live_data = {
            'prices': {},
            'funding_rates': {},
            'open_interest': {},
            'volumes': {},
            'last_update': 0
        }
        
    def add_callback(self, callback: Callable):
        """Add a callback function to receive live data updates"""
        self.data_callbacks.append(callback)
        
    def _notify_callbacks(self, data_type: str, data: Dict):
        """Notify all registered callbacks of new data"""
        for callback in self.data_callbacks:
            try:
                callback(data_type, data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    async def connect(self):
        """Establish WebSocket connection with reconnection logic"""
        delay = self.base_delay
        
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                network = "testnet" if self.use_testnet_fallback else "mainnet"
                logger.info(f"Attempting to connect to Hyperliquid {network} WebSocket (attempt {self.reconnect_attempts + 1})")
                
                self.connection = await websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
                
                network = "testnet" if self.use_testnet_fallback else "mainnet"
                logger.info(f"Successfully connected to Hyperliquid {network} WebSocket")
                self.reconnect_attempts = 0
                delay = self.base_delay
                
                # Subscribe to channels
                await self._subscribe()
                
                # Listen for messages
                await self._listen()
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                await self._handle_reconnection(delay)
                delay = min(delay * 2, self.max_delay)
                
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                # Try testnet fallback if mainnet fails after a few attempts
                if not self.use_testnet_fallback and self.reconnect_attempts >= 3:
                    logger.info("Switching to testnet WebSocket as fallback")
                    self.ws_url = self.testnet_ws_url
                    self.use_testnet_fallback = True
                    self.reconnect_attempts = 0  # Reset attempts for testnet
                
                await self._handle_reconnection(delay)
                delay = min(delay * 2, self.max_delay)
    
    async def _handle_reconnection(self, delay: float):
        """Handle reconnection with exponential backoff"""
        self.reconnect_attempts += 1
        if self.reconnect_attempts < self.max_reconnect_attempts:
            logger.info(f"Reconnecting in {delay} seconds...")
            await asyncio.sleep(delay)
        else:
            logger.error("Max reconnection attempts reached. Stopping WebSocket listener.")
            self.running = False
    
    async def _subscribe(self):
        """Subscribe to Hyperliquid WebSocket channels"""
        subscriptions = [
            # Subscribe to all mids (mark prices)
            {
                "method": "subscribe",
                "subscription": {
                    "type": "allMids"
                }
            },
            # Subscribe to level 1 order book
            {
                "method": "subscribe", 
                "subscription": {
                    "type": "l1Book",
                    "coin": "*"  # All coins
                }
            },
            # Subscribe to trades
            {
                "method": "subscribe",
                "subscription": {
                    "type": "trades",
                    "coin": "*"
                }
            },
            # Subscribe to funding rates
            {
                "method": "subscribe",
                "subscription": {
                    "type": "meta"
                }
            }
        ]
        
        for subscription in subscriptions:
            try:
                await self.connection.send(json.dumps(subscription))
                logger.debug(f"Subscribed to {subscription['subscription']['type']}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {subscription}: {e}")
    
    async def _listen(self):
        """Listen for WebSocket messages"""
        async for message in self.connection:
            try:
                data = json.loads(message)
                await self._process_message(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode WebSocket message: {e}")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
    
    async def _process_message(self, data: Dict):
        """Process incoming WebSocket messages"""
        try:
            channel = data.get('channel', '')
            message_data = data.get('data', {})
            
            current_time = int(time.time() * 1000)
            
            if channel == 'allMids':
                # Process mark prices
                await self._process_all_mids(message_data, current_time)
                
            elif channel == 'l1Book':
                # Process level 1 order book data
                await self._process_l1_book(message_data, current_time)
                
            elif channel == 'trades':
                # Process trade data
                await self._process_trades(message_data, current_time)
                
            elif channel == 'meta':
                # Process funding rates and metadata
                await self._process_meta(message_data, current_time)
                
            self.live_data['last_update'] = current_time
            
        except Exception as e:
            logger.error(f"Error processing message data: {e}")
    
    async def _process_all_mids(self, data: Dict, timestamp: int):
        """Process all mids (mark prices) data"""
        if isinstance(data, list):
            for mid_data in data:
                coin = mid_data.get('coin', '')
                px = float(mid_data.get('px', 0))
                
                if coin and px > 0:
                    self.live_data['prices'][coin] = {
                        'mark_price': px,
                        'timestamp': timestamp,
                        'source': 'hyperliquid_ws'
                    }
                    
            # Notify callbacks
            self._notify_callbacks('prices', self.live_data['prices'])
    
    async def _process_l1_book(self, data: Dict, timestamp: int):
        """Process level 1 order book data"""
        coin = data.get('coin', '')
        levels = data.get('levels', [])
        
        if coin and levels:
            if len(levels) >= 2:
                bids = levels[1] if len(levels[1]) > 0 else []
                asks = levels[0] if len(levels[0]) > 0 else []
                
                if bids and asks:
                    best_bid = float(bids[0].get('px', 0))
                    best_ask = float(asks[0].get('px', 0))
                    spread = ((best_ask - best_bid) / best_bid) * 100 if best_bid > 0 else 0
                    
                    if coin not in self.live_data['prices']:
                        self.live_data['prices'][coin] = {}
                        
                    self.live_data['prices'][coin].update({
                        'best_bid': best_bid,
                        'best_ask': best_ask,
                        'spread_pct': spread,
                        'timestamp': timestamp
                    })
    
    async def _process_trades(self, data: Dict, timestamp: int):
        """Process trade data for volume calculations"""
        if isinstance(data, list):
            for trade in data:
                coin = trade.get('coin', '')
                size = float(trade.get('sz', 0))
                
                if coin:
                    if coin not in self.live_data['volumes']:
                        self.live_data['volumes'][coin] = {
                            'volume_1m': 0,
                            'trade_count': 0,
                            'last_reset': timestamp
                        }
                    
                    # Reset volume counter every minute
                    if timestamp - self.live_data['volumes'][coin]['last_reset'] > 60000:
                        self.live_data['volumes'][coin] = {
                            'volume_1m': size,
                            'trade_count': 1,
                            'last_reset': timestamp
                        }
                    else:
                        self.live_data['volumes'][coin]['volume_1m'] += size
                        self.live_data['volumes'][coin]['trade_count'] += 1
    
    async def _process_meta(self, data: Dict, timestamp: int):
        """Process metadata including funding rates"""
        universe = data.get('universe', [])
        
        for asset in universe:
            coin = asset.get('name', '')
            if coin:
                funding = asset.get('funding', {})
                funding_rate = float(funding.get('funding', 0))
                predicted_funding = float(funding.get('predictedFunding', 0))
                
                self.live_data['funding_rates'][coin] = {
                    'current_funding_rate': funding_rate,
                    'predicted_funding_rate': predicted_funding,
                    'timestamp': timestamp
                }
                
                # Also extract open interest if available
                oi = float(asset.get('openInterest', 0))
                if oi > 0:
                    self.live_data['open_interest'][coin] = {
                        'open_interest': oi,
                        'timestamp': timestamp
                    }
        
        # Notify callbacks
        self._notify_callbacks('funding_rates', self.live_data['funding_rates'])
        self._notify_callbacks('open_interest', self.live_data['open_interest'])
    
    def get_live_data(self) -> Dict:
        """Get current live data snapshot"""
        return self.live_data.copy()
    
    def get_price(self, coin: str) -> Optional[Dict]:
        """Get live price for a specific coin"""
        return self.live_data['prices'].get(coin)
    
    def get_funding_rate(self, coin: str) -> Optional[Dict]:
        """Get funding rate for a specific coin"""
        return self.live_data['funding_rates'].get(coin)
    
    def start_background_listener(self):
        """Start WebSocket listener in background thread"""
        def run_listener():
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Handle shutdown signals
            def signal_handler(signum, frame):
                logger.info("Received shutdown signal")
                self.stop()
                loop.stop()
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            try:
                self.running = True
                loop.run_until_complete(self.connect())
            except Exception as e:
                logger.error(f"Error in WebSocket listener thread: {e}")
            finally:
                loop.close()
        
        thread = Thread(target=run_listener, daemon=True)
        thread.start()
        logger.info("Started Hyperliquid WebSocket listener in background thread")
        return thread
    
    def start(self):
        """Start the WebSocket listener"""
        logger.info("Starting Hyperliquid WebSocket listener")
        self.running = True
        # Start the connection coroutine
        asyncio.create_task(self.connect())
    
    def stop(self):
        """Stop the WebSocket listener"""
        logger.info("Stopping Hyperliquid WebSocket listener")
        self.running = False
        if self.connection:
            asyncio.create_task(self.connection.close())

# Shared price store for caching WebSocket data
class PriceStore:
    """Shared storage for live price data from WebSocket"""
    
    def __init__(self):
        self.data = {}
        self.last_update = 0
        
    def update_prices(self, data_type: str, data: Dict):
        """Update stored data from WebSocket callbacks"""
        self.data[data_type] = data
        self.last_update = int(time.time() * 1000)
        
    def get_data(self, data_type: str) -> Dict:
        """Get stored data by type"""
        return self.data.get(data_type, {})
    
    def get_all_data(self) -> Dict:
        """Get all stored data"""
        return self.data.copy()