import json
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from db.mongo import init_db, get_db
from utils.auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_json_file(filename):
    """Load JSON data from file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'r') as f:
        return json.load(f)

def seed_users():
    """Seed users collection"""
    logger.info("Seeding users...")
    db = get_db()
    users = db.users
    
    # Clear existing users
    users.delete_many({})
    
    users_data = load_json_file('seed_users.json')
    
    for user in users_data:
        # Hash password
        user['password_hash'] = hash_password(user['password'])
        del user['password']
        
        # Add timestamps
        user['created_at'] = datetime.utcnow()
        user['is_active'] = True
        
        users.insert_one(user)
        logger.info(f"Created user: {user['email']}")
    
    logger.info(f"Seeded {len(users_data)} users")

def seed_customers():
    """Seed customers collection"""
    logger.info("Seeding customers...")
    db = get_db()
    customers = db.customers
    
    # Clear existing customers
    customers.delete_many({})
    
    customers_data = load_json_file('seed_customers.json')
    
    for customer in customers_data:
        customer['created_at'] = datetime.utcnow()
        customers.insert_one(customer)
        logger.info(f"Created customer: {customer['name']}")
    
    logger.info(f"Seeded {len(customers_data)} customers")

def seed_accounts():
    """Seed accounts collection"""
    logger.info("Seeding accounts...")
    db = get_db()
    accounts = db.accounts
    
    # Clear existing accounts
    accounts.delete_many({})
    
    accounts_data = load_json_file('seed_accounts.json')
    
    for account in accounts_data:
        # Convert date strings to datetime
        account['invoice_date'] = datetime.fromisoformat(account['invoice_date'].replace('Z', '+00:00'))
        account['due_date'] = datetime.fromisoformat(account['due_date'].replace('Z', '+00:00'))
        account['created_at'] = datetime.utcnow()
        account['updated_at'] = datetime.utcnow()
        
        accounts.insert_one(account)
        logger.info(f"Created account: {account['account_number']}")
    
    logger.info(f"Seeded {len(accounts_data)} accounts")

def seed_dcas():
    """Seed DCAs collection"""
    logger.info("Seeding DCAs...")
    db = get_db()
    dcas = db.dcas
    
    # Clear existing DCAs
    dcas.delete_many({})
    
    dcas_data = load_json_file('seed_dcas.json')
    
    for dca in dcas_data:
        dca['created_at'] = datetime.utcnow()
        dca['updated_at'] = datetime.utcnow()
        
        dcas.insert_one(dca)
        logger.info(f"Created DCA: {dca['name']}")
    
    logger.info(f"Seeded {len(dcas_data)} DCAs")

def seed_all():
    """Seed all collections"""
    try:
        # Initialize database connection
        init_db()
        
        # Seed in order due to dependencies
        seed_users()
        seed_customers()
        seed_dcas()
        seed_accounts()
        
        logger.info("✅ Database seeding completed successfully!")
        logger.info("\nDemo Login Credentials:")
        logger.info("FedEx Admin: admin@fedex.com / password123")
        logger.info("DCA User: dca1@agency.com / password123")
        
    except Exception as e:
        logger.error(f"❌ Error seeding database: {str(e)}")
        raise

if __name__ == '__main__':
    seed_all()
