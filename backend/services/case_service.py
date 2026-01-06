from db.models import (
    get_cases_collection,
    get_accounts_collection,
    get_customers_collection,
    create_case,
    create_event,
    update_case_status,
    create_account
)
from services.ai_service import predict_recovery
from services.workflow_service import calculate_sla_deadline, determine_priority
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

def create_case_with_account(account_number, customer_name, amount, priority='medium',
                             days_past_due=0, customer_email=None, customer_phone=None,
                             notes=None, assigned_dca=None, user_id=None):
    """
    Create a new case along with account and customer if they don't exist.
    This is for manual case creation from the UI.
    """
    try:
        accounts = get_accounts_collection()
        customers = get_customers_collection()
        
        # Check if account already exists
        account = accounts.find_one({'account_number': account_number})
        
        if account:
            # Account exists but might be in use
            if account.get('status') not in ['new', 'recovered', 'written_off']:
                raise ValueError(f"Account {account_number} already has an active case")
            customer_id = account.get('customer_id')
        else:
            # Create new customer
            customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
            customer_data = {
                'customer_id': customer_id,
                'name': customer_name,
                'email': customer_email or '',
                'phone': customer_phone or '',
                'address': {},
                'payment_history': [],
                'risk_score': 50.0,
                'created_at': datetime.utcnow()
            }
            customers.insert_one(customer_data)
            
            # Create new account
            invoice_date = datetime.utcnow() - timedelta(days=days_past_due)
            due_date = invoice_date + timedelta(days=30)
            
            account_data = {
                'account_number': account_number,
                'customer_id': customer_id,
                'amount_overdue': amount,
                'original_amount': amount,
                'overdue_days': days_past_due,
                'invoice_date': invoice_date,
                'due_date': due_date,
                'status': 'new'
            }
            create_account(account_data)
            
            account = account_data
        
        # Calculate SLA deadline
        sla_deadline = calculate_sla_deadline(priority)
        
        # Get AI prediction
        try:
            prediction = predict_recovery(account_number, assigned_dca)
        except Exception as e:
            logger.warning(f"AI prediction failed: {str(e)}")
            prediction = {
                'recovery_probability': 0.5,
                'expected_recovery': amount * 0.5,
                'expected_days': 30
            }
        
        # Create case
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        case_data = {
            'case_id': case_id,
            'account_number': account_number,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'amount': amount,
            'priority': priority,
            'sla_deadline': sla_deadline,
            'recovery_probability': prediction.get('recovery_probability', 0.5),
            'expected_recovery': prediction.get('expected_recovery', 0),
            'expected_days': prediction.get('expected_days', 30),
            'assigned_dca': assigned_dca,
            'status': 'assigned' if assigned_dca else 'pending',
            'notes': [notes] if notes else [],
            'actions': []
        }
        
        result = create_case(case_data)
        
        # Update account status
        accounts.update_one(
            {'account_number': account_number},
            {'$set': {'status': 'assigned', 'updated_at': datetime.utcnow()}}
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': 'case_created',
            'description': f'Case created manually for {customer_name}',
            'user_id': user_id or 'system',
            'metadata': {
                'priority': priority,
                'amount': amount,
                'assigned_dca': assigned_dca,
                'notes': notes
            }
        })
        
        logger.info(f"Case {case_id} created for new account {account_number}")
        
        # Return case data
        case_data['_id'] = str(result.inserted_id)
        case_data['created_at'] = datetime.utcnow().isoformat()
        
        return case_data
        
    except Exception as e:
        logger.error(f"Error creating case with account: {str(e)}")
        raise

def create_new_case(account_number, priority=None, user_id=None):
    """
    Create a new case from an overdue account
    """
    try:
        accounts = get_accounts_collection()
        account = accounts.find_one({'account_number': account_number})
        
        if not account:
            raise ValueError(f"Account {account_number} not found")
        
        if account['status'] != 'new':
            raise ValueError(f"Account {account_number} already has a case")
        
        # Determine priority
        if not priority:
            priority = determine_priority(account)
        
        # Calculate SLA deadline
        sla_deadline = calculate_sla_deadline(priority)
        
        # Get AI prediction
        try:
            prediction = predict_recovery(account_number, None)
        except Exception as e:
            logger.warning(f"AI prediction failed: {str(e)}")
            prediction = {
                'recovery_probability': 0.5,
                'expected_recovery': account['amount_overdue'] * 0.5,
                'expected_days': 30
            }
        
        # Create case
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        case_data = {
            'case_id': case_id,
            'account_number': account_number,
            'customer_id': account['customer_id'],
            'amount': account['amount_overdue'],
            'priority': priority,
            'sla_deadline': sla_deadline,
            'recovery_probability': prediction.get('recovery_probability', 0.5),
            'expected_recovery': prediction.get('expected_recovery', 0),
            'expected_days': prediction.get('expected_days', 30)
        }
        
        result = create_case(case_data)
        
        # Update account status
        accounts.update_one(
            {'account_number': account_number},
            {'$set': {'status': 'assigned', 'updated_at': datetime.utcnow()}}
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': 'case_created',
            'description': f'Case created for account {account_number}',
            'user_id': user_id or 'system',
            'metadata': {'priority': priority, 'amount': account['amount_overdue']}
        })
        
        logger.info(f"Case {case_id} created for account {account_number}")
        
        # Return case data
        case_data['_id'] = str(result.inserted_id)
        case_data['created_at'] = datetime.utcnow().isoformat()
        case_data['status'] = 'pending'
        
        return case_data
        
    except Exception as e:
        logger.error(f"Error creating case: {str(e)}")
        raise

def assign_case_to_dca(case_id, dca_id, user_id):
    """
    Assign a case to a DCA
    """
    try:
        from db.models import get_dcas_collection
        
        cases = get_cases_collection()
        dcas = get_dcas_collection()
        
        case = cases.find_one({'case_id': case_id})
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        dca = dcas.find_one({'dca_id': dca_id})
        if not dca:
            raise ValueError(f"DCA {dca_id} not found")
        
        if dca['status'] != 'active':
            raise ValueError(f"DCA {dca_id} is not active")
        
        if dca['current_cases'] >= dca['capacity']:
            raise ValueError(f"DCA {dca_id} is at full capacity")
        
        # Update case
        cases.update_one(
            {'case_id': case_id},
            {
                '$set': {
                    'assigned_dca': dca_id,
                    'assigned_at': datetime.utcnow(),
                    'status': 'assigned',
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        # Update DCA case count
        dcas.update_one(
            {'dca_id': dca_id},
            {
                '$inc': {'current_cases': 1},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': 'case_assigned',
            'description': f'Case assigned to DCA {dca["name"]}',
            'user_id': user_id,
            'metadata': {'dca_id': dca_id, 'dca_name': dca['name']}
        })
        
        logger.info(f"Case {case_id} assigned to DCA {dca_id}")
        
        # Return updated case
        updated_case = cases.find_one({'case_id': case_id})
        updated_case['_id'] = str(updated_case['_id'])
        return updated_case
        
    except Exception as e:
        logger.error(f"Error assigning case: {str(e)}")
        raise

def update_case_status_service(case_id, status, user_id, notes=''):
    """
    Update case status
    """
    try:
        cases = get_cases_collection()
        
        case = cases.find_one({'case_id': case_id})
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        if status == 'resolved':
            update_data['resolved_at'] = datetime.utcnow()
        
        cases.update_one(
            {'case_id': case_id},
            {'$set': update_data}
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': 'status_change',
            'description': f'Status changed to {status}. {notes}',
            'user_id': user_id,
            'metadata': {'old_status': case['status'], 'new_status': status}
        })
        
        logger.info(f"Case {case_id} status updated to {status}")
        
        # Return updated case
        updated_case = cases.find_one({'case_id': case_id})
        updated_case['_id'] = str(updated_case['_id'])
        return updated_case
        
    except Exception as e:
        logger.error(f"Error updating case status: {str(e)}")
        raise

def get_case_details(case_id):
    """
    Get detailed information about a case
    """
    try:
        cases = get_cases_collection()
        events = get_events_collection()
        
        case = cases.find_one({'case_id': case_id})
        if not case:
            return None
        
        # Get case history
        case_events = list(events.find(
            {'case_id': case_id}
        ).sort('timestamp', -1))
        
        case['_id'] = str(case['_id'])
        case['history'] = case_events
        
        # Convert datetime to string for top-level fields
        for key in ['created_at', 'assigned_at', 'resolved_at', 'updated_at', 'sla_deadline', 'due_date']:
            if key in case and case[key]:
                if hasattr(case[key], 'isoformat'):
                    case[key] = case[key].isoformat()
                else:
                    case[key] = str(case[key])
        
        # Convert datetime in notes array
        if 'notes' in case and isinstance(case['notes'], list):
            for note in case['notes']:
                if 'timestamp' in note and hasattr(note['timestamp'], 'isoformat'):
                    note['timestamp'] = note['timestamp'].isoformat()
        
        # Convert datetime in actions array
        if 'actions' in case and isinstance(case['actions'], list):
            for action in case['actions']:
                if 'timestamp' in action and hasattr(action['timestamp'], 'isoformat'):
                    action['timestamp'] = action['timestamp'].isoformat()
        
        # Convert datetime in history/events
        for event in case_events:
            if '_id' in event:
                event['_id'] = str(event['_id'])
            if 'timestamp' in event and hasattr(event['timestamp'], 'isoformat'):
                event['timestamp'] = event['timestamp'].isoformat()
        
        return case
        
    except Exception as e:
        logger.error(f"Error getting case details: {str(e)}")
        raise

def get_all_cases(filters, limit=50, offset=0):
    """
    Get list of cases with filters
    """
    try:
        cases = get_cases_collection()
        
        case_list = list(cases.find(filters)
                        .sort('created_at', -1)
                        .skip(offset)
                        .limit(limit))
        
        # Convert ObjectId and datetime to string
        for case in case_list:
            case['_id'] = str(case['_id'])
            
            # Convert top-level datetime fields
            for key in ['created_at', 'assigned_at', 'resolved_at', 'updated_at', 'sla_deadline', 'due_date']:
                if key in case and case[key]:
                    if hasattr(case[key], 'isoformat'):
                        case[key] = case[key].isoformat()
                    else:
                        case[key] = str(case[key])
            
            # Convert datetime in notes array
            if 'notes' in case and isinstance(case['notes'], list):
                for note in case['notes']:
                    if 'timestamp' in note and hasattr(note['timestamp'], 'isoformat'):
                        note['timestamp'] = note['timestamp'].isoformat()
            
            # Convert datetime in actions array
            if 'actions' in case and isinstance(case['actions'], list):
                for action in case['actions']:
                    if 'timestamp' in action and hasattr(action['timestamp'], 'isoformat'):
                        action['timestamp'] = action['timestamp'].isoformat()
        
        return case_list
        
    except Exception as e:
        logger.error(f"Error getting cases: {str(e)}")
        raise

def add_case_note(case_id, note, user_id):
    """
    Add a note to a case
    """
    try:
        from db.models import get_users_collection
        
        cases = get_cases_collection()
        users = get_users_collection()
        
        # Get user info for author name
        user = users.find_one({'user_id': user_id})
        author_name = user.get('name', user.get('email', 'Unknown')) if user else 'System'
        
        note_data = {
            'content': note,  # Use 'content' instead of 'note'
            'author': author_name,  # Add author name
            'user_id': user_id,
            'timestamp': datetime.utcnow()
        }
        
        cases.update_one(
            {'case_id': case_id},
            {
                '$push': {'notes': note_data},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': 'note_added',
            'description': f'Note added by {author_name}: {note[:50]}{"..." if len(note) > 50 else ""}',
            'user_id': user_id,
            'metadata': {'note': note}
        })
        
        logger.info(f"Note added to case {case_id} by {author_name}")
        
        # Return updated case
        updated_case = cases.find_one({'case_id': case_id})
        updated_case['_id'] = str(updated_case['_id'])
        
        # Convert datetime in notes
        if 'notes' in updated_case and isinstance(updated_case['notes'], list):
            for n in updated_case['notes']:
                if 'timestamp' in n and hasattr(n['timestamp'], 'isoformat'):
                    n['timestamp'] = n['timestamp'].isoformat()
        
        return updated_case
        
    except Exception as e:
        logger.error(f"Error adding note: {str(e)}")
        raise

def add_case_action(case_id, action_type, description, user_id, amount=0):
    """
    Add an action to a case (e.g., call, email, payment)
    """
    try:
        cases = get_cases_collection()
        
        action_data = {
            'action_type': action_type,
            'description': description,
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'amount': amount
        }
        
        cases.update_one(
            {'case_id': case_id},
            {
                '$push': {'actions': action_data},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': action_type,
            'description': description,
            'user_id': user_id,
            'metadata': {'amount': amount}
        })
        
        # Return updated case
        updated_case = cases.find_one({'case_id': case_id})
        updated_case['_id'] = str(updated_case['_id'])
        return updated_case
        
    except Exception as e:
        logger.error(f"Error adding action: {str(e)}")
        raise

def escalate_case(case_id, reason, user_id):
    """
    Escalate a case
    """
    try:
        cases = get_cases_collection()
        
        cases.update_one(
            {'case_id': case_id},
            {
                '$set': {
                    'status': 'escalated',
                    'updated_at': datetime.utcnow(),
                    'escalation_reason': reason
                }
            }
        )
        
        # Log event
        create_event({
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': 'escalated',
            'description': f'Case escalated: {reason}',
            'user_id': user_id,
            'metadata': {'reason': reason}
        })
        
        logger.info(f"Case {case_id} escalated")
        
        # Return updated case
        updated_case = cases.find_one({'case_id': case_id})
        updated_case['_id'] = str(updated_case['_id'])
        return updated_case
        
    except Exception as e:
        logger.error(f"Error escalating case: {str(e)}")
        raise

from db.models import get_events_collection
