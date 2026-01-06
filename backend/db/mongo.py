from pymongo import MongoClient, ASCENDING, DESCENDING
from config import Config
import logging

logger = logging.getLogger(__name__)

# Global MongoDB client and database
mongo_client = None
db = None

def init_db():
    """Initialize MongoDB connection"""
    global mongo_client, db
    
    try:
        mongo_client = MongoClient(Config.MONGO_URI)
        db = mongo_client[Config.MONGO_DB_NAME]
        
        # Test connection
        mongo_client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {Config.MONGO_DB_NAME}")
        
        # Create indexes
        create_indexes()
        
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

def get_db():
    """Get database instance"""
    global db
    if db is None:
        init_db()
    return db

def create_indexes():
    """Create indexes for better query performance"""
    try:
        database = get_db()
        
        # Users collection indexes
        database.users.create_index([("email", ASCENDING)], unique=True)
        database.users.create_index([("role", ASCENDING)])
        
        # Accounts collection indexes
        database.accounts.create_index([("account_number", ASCENDING)], unique=True)
        database.accounts.create_index([("status", ASCENDING)])
        database.accounts.create_index([("overdue_days", DESCENDING)])
        database.accounts.create_index([("amount_overdue", DESCENDING)])
        
        # Customers collection indexes
        database.customers.create_index([("customer_id", ASCENDING)], unique=True)
        database.customers.create_index([("email", ASCENDING)])
        
        # DCAs collection indexes
        database.dcas.create_index([("dca_id", ASCENDING)], unique=True)
        database.dcas.create_index([("status", ASCENDING)])
        database.dcas.create_index([("performance_score", DESCENDING)])
        
        # Cases collection indexes
        database.cases.create_index([("case_id", ASCENDING)], unique=True)
        database.cases.create_index([("account_number", ASCENDING)])
        database.cases.create_index([("assigned_dca", ASCENDING)])
        database.cases.create_index([("status", ASCENDING)])
        database.cases.create_index([("priority", DESCENDING)])
        database.cases.create_index([("sla_deadline", ASCENDING)])
        database.cases.create_index([("created_at", DESCENDING)])
        
        # Events collection indexes
        database.events.create_index([("case_id", ASCENDING)])
        database.events.create_index([("event_type", ASCENDING)])
        database.events.create_index([("timestamp", DESCENDING)])
        database.events.create_index([("user_id", ASCENDING)])
        
        # Predictions collection indexes
        database.predictions.create_index([("account_number", ASCENDING)])
        database.predictions.create_index([("case_id", ASCENDING)])
        database.predictions.create_index([("created_at", DESCENDING)])
        database.predictions.create_index([("recovery_probability", DESCENDING)])
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")
        raise

def close_db():
    """Close MongoDB connection"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed")
