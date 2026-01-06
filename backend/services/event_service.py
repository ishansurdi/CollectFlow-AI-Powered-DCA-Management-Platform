from db.models import create_event
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

def log_case_event(case_id, event_type, description, user_id, metadata=None):
    """
    Log a case-related event
    """
    try:
        event_data = {
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': case_id,
            'event_type': event_type,
            'description': description,
            'user_id': user_id,
            'metadata': metadata or {}
        }
        
        create_event(event_data)
        logger.info(f"Event logged: {event_type} for case {case_id}")
        
    except Exception as e:
        logger.error(f"Error logging event: {str(e)}")
        raise

def log_system_event(event_type, description, metadata=None):
    """
    Log a system-level event
    """
    try:
        event_data = {
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': None,
            'event_type': event_type,
            'description': description,
            'user_id': 'system',
            'metadata': metadata or {}
        }
        
        create_event(event_data)
        logger.info(f"System event logged: {event_type}")
        
    except Exception as e:
        logger.error(f"Error logging system event: {str(e)}")
        raise

def log_user_action(user_id, action, resource_type, resource_id, metadata=None):
    """
    Log a user action for audit trail
    """
    try:
        event_data = {
            'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
            'case_id': resource_id if resource_type == 'case' else None,
            'event_type': 'user_action',
            'description': f"User {user_id} performed {action} on {resource_type} {resource_id}",
            'user_id': user_id,
            'metadata': {
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                **(metadata or {})
            }
        }
        
        create_event(event_data)
        
    except Exception as e:
        logger.error(f"Error logging user action: {str(e)}")
        raise

def get_event_history(case_id=None, user_id=None, event_type=None, limit=100):
    """
    Get event history with filters
    """
    try:
        from db.models import get_events_collection
        events = get_events_collection()
        
        filters = {}
        if case_id:
            filters['case_id'] = case_id
        if user_id:
            filters['user_id'] = user_id
        if event_type:
            filters['event_type'] = event_type
        
        event_list = list(events.find(filters)
                         .sort('timestamp', -1)
                         .limit(limit))
        
        # Convert ObjectId and datetime to string
        for event in event_list:
            event['_id'] = str(event['_id'])
            event['timestamp'] = event['timestamp'].isoformat()
        
        return event_list
        
    except Exception as e:
        logger.error(f"Error getting event history: {str(e)}")
        raise
