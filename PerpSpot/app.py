import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from utils.logger import setup_logger

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///arbitrage.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Initialize services after app context is available
arbitrage_service = None
scheduler = BackgroundScheduler()

def create_tables():
    """Create database tables"""
    with app.app_context():
        # Import models to register them
        import models  # noqa: F401
        db.create_all()
        logger.info("Database tables created successfully")

def update_prices():
    """Background task to update prices every 10 seconds"""
    try:
        with app.app_context():
            logger.debug("Updating prices...")
            if arbitrage_service:
                arbitrage_service.update_all_prices()
                logger.debug("Price update completed")
    except Exception as e:
        logger.error(f"Error updating prices: {str(e)}")

# Register blueprints
from routes.main import main_bp
from routes.api import api_bp

app.register_blueprint(main_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Initialize services after blueprints are registered
with app.app_context():
    create_tables()
    
    # Import and initialize arbitrage service
    from services.arbitrage_service import ArbitrageService
    from services.bridge_service import bridge_service
    arbitrage_service = ArbitrageService()
    
    # Enable real-time WebSocket streaming with mainnet/testnet fallback
    arbitrage_service.enable_realtime_streaming()
    
    # Connect bridge service to arbitrage service
    bridge_service.arbitrage_service = arbitrage_service

# Start background scheduler
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler.add_job(
        func=update_prices,
        trigger=IntervalTrigger(seconds=10),
        id='price_update_job',
        name='Update cryptocurrency prices every 10 seconds',
        replace_existing=True
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    logger.info("Background price update scheduler started")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
