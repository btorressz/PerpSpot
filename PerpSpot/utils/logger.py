import logging
import sys
from datetime import datetime
import os

def setup_logger():
    """Setup logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    log_level = logging.DEBUG if os.getenv('FLASK_DEBUG', 'true').lower() == 'true' else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler
    log_filename = f"{log_dir}/arbitrage_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler]
    )
    
    # Set specific logger levels
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("="*50)
    logger.info("Crypto Arbitrage Platform Started")
    logger.info("="*50)
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Log file: {log_filename}")

class RequestLogger:
    """Middleware to log API requests"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        app.before_request(self.log_request)
        app.after_request(self.log_response)
    
    def log_request(self):
        logger = logging.getLogger('api_requests')
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    
    def log_response(self, response):
        logger = logging.getLogger('api_requests')
        logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
        return response

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)
