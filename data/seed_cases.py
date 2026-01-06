import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from db.mongo import init_db, get_db
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_case_id():
    """Generate unique case ID"""
    return f"CASE-{datetime.now().strftime('%Y%m')}-{random.randint(1000, 9999)}"

def create_cases_from_accounts():
    """Create cases from existing accounts"""
    logger.info("Creating cases from accounts...")
    init_db()
    db = get_db()
    
    # Get all accounts and DCAs
    accounts = list(db.accounts.find({}))
    dcas = list(db.dcas.find({}))
    
    if not accounts:
        logger.error("No accounts found. Please run seed_database.py first")
        return
    
    if not dcas:
        logger.error("No DCAs found. Please run seed_database.py first")
        return
    
    cases_collection = db.cases
    
    # Clear existing cases
    cases_collection.delete_many({})
    
    priorities = ['critical', 'high', 'medium', 'low']
    statuses = ['pending', 'assigned', 'in_progress', 'resolved']
    
    cases = []
    
    for account in accounts:
        # Create 1-2 cases per account
        num_cases = random.randint(1, 2)
        
        for i in range(num_cases):
            # Randomly assign to DCA or leave pending
            assigned_dca = None
            dca_id = None
            status = random.choice(statuses)
            
            if status in ['assigned', 'in_progress', 'resolved']:
                dca = random.choice(dcas)
                assigned_dca = dca['name']
                dca_id = str(dca['_id'])
            
            # Calculate dates
            created_days_ago = random.randint(5, 60)
            created_at = datetime.utcnow() - timedelta(days=created_days_ago)
            
            # Get customer name from customer_id
            customer = db.customers.find_one({'customer_id': account['customer_id']})
            customer_name = customer['name'] if customer else account['customer_id']
            
            case = {
                'case_id': generate_case_id(),
                'account_number': account['account_number'],
                'customer_name': customer_name,
                'customer_id': account['customer_id'],
                'amount': float(account['amount_overdue']),
                'original_amount': float(account['original_amount']),
                'priority': random.choice(priorities),
                'status': status,
                'assigned_dca': assigned_dca,
                'dca_id': dca_id,
                'created_at': created_at,
                'updated_at': datetime.utcnow(),
                'due_date': account['due_date'],
                'days_overdue': int(account['overdue_days']),
                'notes': [
                    {
                        'author': 'System',
                        'content': 'Case created automatically from overdue account',
                        'timestamp': created_at
                    }
                ],
                'actions': [],
                'sla_status': 'on_track' if (datetime.utcnow() - created_at).days < 14 else 'at_risk',
                'sla_deadline': created_at + timedelta(days=14),
                'metadata': {
                    'source': 'automatic',
                    'account_id': str(account['_id'])
                }
            }
            
            # Add some notes for non-pending cases
            if status == 'assigned':
                case['notes'].append({
                    'author': assigned_dca,
                    'content': 'Case assigned and under review',
                    'timestamp': created_at + timedelta(days=1)
                })
            
            if status == 'in_progress':
                case['notes'].append({
                    'author': assigned_dca,
                    'content': 'Contact attempt made with customer',
                    'timestamp': created_at + timedelta(days=2)
                })
                case['actions'].append({
                    'action_type': 'contact',
                    'description': 'Phone call made to customer',
                    'timestamp': created_at + timedelta(days=2),
                    'performed_by': assigned_dca
                })
            
            if status == 'resolved':
                case['notes'].append({
                    'author': assigned_dca,
                    'content': 'Payment received and case resolved',
                    'timestamp': created_at + timedelta(days=5)
                })
                case['actions'].append({
                    'action_type': 'payment',
                    'description': 'Full payment received',
                    'amount': float(account['amount_overdue']),
                    'timestamp': created_at + timedelta(days=5),
                    'performed_by': assigned_dca
                })
                case['resolved_at'] = created_at + timedelta(days=5)
                case['resolution'] = 'Payment received in full'
            
            cases.append(case)
    
    # Insert all cases
    if cases:
        result = cases_collection.insert_many(cases)
        logger.info(f"✅ Created {len(result.inserted_ids)} cases successfully!")
        
        # Print summary
        logger.info("\nCases Summary:")
        for status in statuses:
            count = len([c for c in cases if c['status'] == status])
            logger.info(f"  {status}: {count}")
        
        logger.info(f"\nTotal cases created: {len(cases)}")
    else:
        logger.warning("No cases were created")

if __name__ == '__main__':
    create_cases_from_accounts()
