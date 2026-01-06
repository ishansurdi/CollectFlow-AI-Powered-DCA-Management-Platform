import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'fedex-dca-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # MongoDB settings
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'fedex_dca')
    
    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    
    # SLA settings (in hours)
    SLA_CRITICAL = int(os.getenv('SLA_CRITICAL', 24))
    SLA_HIGH = int(os.getenv('SLA_HIGH', 48))
    SLA_MEDIUM = int(os.getenv('SLA_MEDIUM', 72))
    SLA_LOW = int(os.getenv('SLA_LOW', 120))
    
    # AI Model settings
    MODEL_PATH = os.getenv('MODEL_PATH', './backend/ai_models/saved_models/')
    RETRAIN_INTERVAL_DAYS = int(os.getenv('RETRAIN_INTERVAL_DAYS', 7))
    
    # DCA settings
    MAX_CASES_PER_DCA = int(os.getenv('MAX_CASES_PER_DCA', 50))
    
    # Scoring weights
    SCORE_WEIGHT_AMOUNT = float(os.getenv('SCORE_WEIGHT_AMOUNT', 0.3))
    SCORE_WEIGHT_AGE = float(os.getenv('SCORE_WEIGHT_AGE', 0.2))
    SCORE_WEIGHT_PROBABILITY = float(os.getenv('SCORE_WEIGHT_PROBABILITY', 0.5))
