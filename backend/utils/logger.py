import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(name=None, log_file=None, level=logging.INFO):
    """
    Setup application logger with console and file handlers
    """
    logger = logging.getLogger(name or 'fedex_dca')
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if not log_file:
        log_dir = './logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/fedex_dca_{datetime.now().strftime('%Y%m%d')}.log"
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_log_file = log_file.replace('.log', '_errors.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    logger.info("Logger initialized")
    
    return logger

def log_request(request):
    """
    Log HTTP request details
    """
    logger = logging.getLogger('fedex_dca')
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")

def log_response(response, duration_ms):
    """
    Log HTTP response details
    """
    logger = logging.getLogger('fedex_dca')
    logger.info(f"Response {response.status_code} in {duration_ms:.2f}ms")

def log_error(error, context=None):
    """
    Log error with context
    """
    logger = logging.getLogger('fedex_dca')
    error_msg = f"Error: {str(error)}"
    if context:
        error_msg += f" | Context: {context}"
    logger.error(error_msg, exc_info=True)

def log_business_event(event_type, description, metadata=None):
    """
    Log business-level events
    """
    logger = logging.getLogger('fedex_dca')
    log_msg = f"Business Event [{event_type}]: {description}"
    if metadata:
        log_msg += f" | {metadata}"
    logger.info(log_msg)
