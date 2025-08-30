from app import db
from datetime import datetime
from sqlalchemy.sql import func

class PriceData(db.Model):
    __tablename__ = 'price_data'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(10), nullable=False)
    source = db.Column(db.String(20), nullable=False)  # 'jupiter', 'hyperliquid', 'coingecko', 'kraken'
    price_type = db.Column(db.String(20), nullable=False)  # 'spot', 'mark', 'index'
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'source': self.source,
            'price_type': self.price_type,
            'price': self.price,
            'timestamp': self.timestamp.isoformat()
        }

class FundingRate(db.Model):
    __tablename__ = 'funding_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(10), nullable=False)
    funding_rate = db.Column(db.Float, nullable=False)
    predicted_funding_rate = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'funding_rate': self.funding_rate,
            'predicted_funding_rate': self.predicted_funding_rate,
            'timestamp': self.timestamp.isoformat()
        }

class ArbitrageOpportunity(db.Model):
    __tablename__ = 'arbitrage_opportunities'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(10), nullable=False)
    spot_price = db.Column(db.Float, nullable=False)
    perp_price = db.Column(db.Float, nullable=False)
    spread_bps = db.Column(db.Float, nullable=False)
    estimated_pnl = db.Column(db.Float)
    strategy = db.Column(db.String(100))  # 'long_spot_short_perp' or 'short_spot_long_perp'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'spot_price': self.spot_price,
            'perp_price': self.perp_price,
            'spread_bps': self.spread_bps,
            'estimated_pnl': self.estimated_pnl,
            'strategy': self.strategy,
            'timestamp': self.timestamp.isoformat()
        }

class SystemStatus(db.Model):
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'online', 'offline', 'rate_limited'
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'service': self.service,
            'status': self.status,
            'last_update': self.last_update.isoformat(),
            'error_message': self.error_message
        }
