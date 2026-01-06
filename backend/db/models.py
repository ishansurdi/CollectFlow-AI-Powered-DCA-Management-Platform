from datetime import datetime
from db.mongo import get_db

"""
MongoDB collections schemas and helper functions
"""

def get_users_collection():
    """Get users collection"""
    return get_db().users

def get_accounts_collection():
    """Get accounts collection"""
    return get_db().accounts

def get_customers_collection():
    """Get customers collection"""
    return get_db().customers

def get_dcas_collection():
    """Get DCAs collection"""
    return get_db().dcas

def get_cases_collection():
    """Get cases collection"""
    return get_db().cases

def get_events_collection():
    """Get events collection"""
    return get_db().events

def get_predictions_collection():
    """Get predictions collection"""
    return get_db().predictions

def get_insights_collection():
    """Get insights collection (for learning agent)"""
    return get_db().insights

# Schema definitions (for reference and validation)

USER_SCHEMA = {
    "user_id": str,          # Unique identifier
    "email": str,            # Login email
    "password_hash": str,    # Bcrypt hashed password
    "role": str,             # 'fedex_admin', 'fedex_user', 'dca_admin', 'dca_agent'
    "name": str,             # Full name
    "dca_id": str,           # For DCA users (optional)
    "created_at": datetime,
    "last_login": datetime,
    "is_active": bool
}

ACCOUNT_SCHEMA = {
    "account_number": str,   # Unique account identifier
    "customer_id": str,      # Link to customer
    "amount_overdue": float, # Outstanding amount
    "original_amount": float,
    "overdue_days": int,     # Days past due
    "invoice_date": datetime,
    "due_date": datetime,
    "status": str,           # 'new', 'assigned', 'in_progress', 'recovered', 'written_off'
    "created_at": datetime,
    "updated_at": datetime
}

CUSTOMER_SCHEMA = {
    "customer_id": str,      # Unique customer identifier
    "name": str,
    "email": str,
    "phone": str,
    "address": dict,         # {street, city, state, zip}
    "payment_history": list, # Historical payment behavior
    "risk_score": float,     # 0-100
    "created_at": datetime
}

DCA_SCHEMA = {
    "dca_id": str,           # Unique DCA identifier
    "name": str,             # DCA company name
    "email": str,
    "phone": str,
    "specialization": list,  # ['commercial', 'retail', 'international']
    "status": str,           # 'active', 'inactive', 'suspended'
    "capacity": int,         # Max concurrent cases
    "current_cases": int,    # Current case count
    "performance_score": float,  # 0-100
    "recovery_rate": float,      # Percentage
    "avg_recovery_time": float,  # Days
    "total_recovered": float,    # Total amount recovered
    "total_cases": int,
    "created_at": datetime,
    "updated_at": datetime
}

CASE_SCHEMA = {
    "case_id": str,          # Unique case identifier
    "account_number": str,   # Link to account
    "customer_id": str,      # Link to customer
    "assigned_dca": str,     # DCA ID (optional)
    "assigned_agent": str,   # Agent user ID (optional)
    "amount": float,         # Case amount
    "priority": str,         # 'critical', 'high', 'medium', 'low'
    "status": str,           # 'pending', 'assigned', 'in_progress', 'resolved', 'escalated'
    "sla_deadline": datetime,
    "recovery_probability": float,  # AI prediction
    "expected_recovery": float,     # AI prediction
    "expected_days": int,           # AI prediction
    "created_at": datetime,
    "assigned_at": datetime,
    "resolved_at": datetime,
    "updated_at": datetime,
    "notes": list,           # Case notes/comments
    "actions": list          # Actions taken
}

EVENT_SCHEMA = {
    "event_id": str,         # Unique event identifier
    "case_id": str,          # Link to case
    "event_type": str,       # 'created', 'assigned', 'contacted', 'payment', 'escalated', etc.
    "description": str,
    "user_id": str,          # Who triggered the event
    "timestamp": datetime,
    "metadata": dict         # Additional context
}

PREDICTION_SCHEMA = {
    "prediction_id": str,    # Unique prediction identifier
    "account_number": str,
    "case_id": str,
    "recovery_probability": float,  # 0-1
    "expected_amount": float,
    "days_to_recover": int,
    "confidence_score": float,      # Model confidence
    "model_version": str,
    "created_at": datetime,
    "features_used": dict    # Feature values used for prediction
}

# Helper functions for common queries

def create_user(user_data):
    """Create a new user"""
    user_data['created_at'] = datetime.utcnow()
    user_data['is_active'] = True
    return get_users_collection().insert_one(user_data)

def create_account(account_data):
    """Create a new account"""
    account_data['created_at'] = datetime.utcnow()
    account_data['updated_at'] = datetime.utcnow()
    account_data['status'] = 'new'
    return get_accounts_collection().insert_one(account_data)

def create_case(case_data):
    """Create a new case"""
    case_data['created_at'] = datetime.utcnow()
    case_data['updated_at'] = datetime.utcnow()
    case_data['status'] = 'pending'
    case_data['notes'] = []
    case_data['actions'] = []
    return get_cases_collection().insert_one(case_data)

def create_event(event_data):
    """Create a new event"""
    event_data['timestamp'] = datetime.utcnow()
    return get_events_collection().insert_one(event_data)

def update_case_status(case_id, status, user_id):
    """Update case status and log event"""
    cases = get_cases_collection()
    result = cases.update_one(
        {"case_id": case_id},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Log event
    create_event({
        "case_id": case_id,
        "event_type": "status_change",
        "description": f"Case status changed to {status}",
        "user_id": user_id,
        "metadata": {"new_status": status}
    })
    
    return result

def get_active_cases_by_dca(dca_id):
    """Get all active cases for a DCA"""
    return get_cases_collection().find({
        "assigned_dca": dca_id,
        "status": {"$in": ["assigned", "in_progress"]}
    })

def get_overdue_sla_cases():
    """Get cases that have breached SLA"""
    return get_cases_collection().find({
        "sla_deadline": {"$lt": datetime.utcnow()},
        "status": {"$nin": ["resolved", "written_off"]}
    })
