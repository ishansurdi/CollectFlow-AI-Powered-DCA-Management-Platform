from flask import Blueprint, request, jsonify
from utils.auth import token_required
from services.case_service import (
    create_new_case,
    assign_case_to_dca,
    update_case_status_service,
    get_case_details,
    get_all_cases,
    add_case_note,
    add_case_action,
    escalate_case
)
import logging

logger = logging.getLogger(__name__)

case_bp = Blueprint('cases', __name__)

@case_bp.route('/', methods=['GET'])
@token_required
def list_cases(current_user):
    """
    Get list of cases based on user role
    Query params: status, priority, assigned_dca, limit, offset
    """
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        assigned_dca = request.args.get('assigned_dca')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Filter based on role
        filters = {}
        if current_user['role'] in ['dca_admin', 'dca_agent']:
            # DCA users only see their own cases
            filters['dca_id'] = current_user.get('dca_id')
        
        if status:
            filters['status'] = status
        if priority:
            filters['priority'] = priority
        if assigned_dca and current_user['role'].startswith('fedex'):
            # FedEx users can filter by DCA
            filters['dca_id'] = assigned_dca
        
        cases = get_all_cases(filters, limit, offset)
        
        return jsonify({
            'cases': cases,
            'count': len(cases)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching cases: {str(e)}")
        return jsonify({'error': 'Failed to fetch cases'}), 500

@case_bp.route('/<case_id>', methods=['GET'])
@token_required
def get_case(current_user, case_id):
    """Get detailed information about a specific case"""
    try:
        case = get_case_details(case_id)
        
        if not case:
            return jsonify({'error': 'Case not found'}), 404
        
        # Check authorization
        if current_user['role'] in ['dca_admin', 'dca_agent']:
            if case.get('dca_id') != current_user.get('dca_id'):
                return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify(case), 200
        
    except Exception as e:
        logger.error(f"Error fetching case {case_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch case'}), 500

@case_bp.route('/', methods=['POST'])
@token_required
def create_case(current_user):
    """
    Create a new case (FedEx users only)
    Supports two modes:
    1. From existing account: {account_number, priority}
    2. New account/case: {account_number, customer_name, amount, priority, days_past_due, customer_email, customer_phone, notes, assigned_dca}
    """
    try:
        if not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        account_number = data.get('account_number')
        
        if not account_number:
            return jsonify({'error': 'Account number required'}), 400
        
        # Check if this is a new account/case creation with full details
        if data.get('customer_name') and data.get('amount'):
            # Import here to avoid circular dependency
            from services.case_service import create_case_with_account
            
            case = create_case_with_account(
                account_number=account_number,
                customer_name=data.get('customer_name'),
                amount=float(data.get('amount')),
                priority=data.get('priority', 'medium'),
                days_past_due=int(data.get('days_past_due', 0)),
                customer_email=data.get('customer_email'),
                customer_phone=data.get('customer_phone'),
                notes=data.get('notes'),
                assigned_dca=data.get('assigned_dca'),
                user_id=current_user['user_id']
            )
        else:
            # Existing account flow
            priority = data.get('priority', 'medium')
            case = create_new_case(account_number, priority, current_user['user_id'])
        
        return jsonify({
            'message': 'Case created successfully',
            'case': case
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating case: {str(e)}")
        return jsonify({'error': str(e)}), 500

@case_bp.route('/<case_id>/assign', methods=['POST'])
@token_required
def assign_case(current_user, case_id):
    """
    Assign case to DCA (FedEx admin only)
    Expected payload: {dca_id}
    """
    try:
        if current_user['role'] != 'fedex_admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        dca_id = data.get('dca_id')
        
        if not dca_id:
            return jsonify({'error': 'DCA ID required'}), 400
        
        case = assign_case_to_dca(case_id, dca_id, current_user['user_id'])
        
        return jsonify({
            'message': 'Case assigned successfully',
            'case': case
        }), 200
        
    except Exception as e:
        logger.error(f"Error assigning case {case_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@case_bp.route('/<case_id>/status', methods=['PUT'])
@token_required
def update_case_status(current_user, case_id):
    """
    Update case status
    Expected payload: {status, notes (optional)}
    """
    try:
        data = request.get_json()
        status = data.get('status')
        notes = data.get('notes', '')
        
        if not status:
            return jsonify({'error': 'Status required'}), 400
        
        case = update_case_status_service(
            case_id,
            status,
            current_user['user_id'],
            notes
        )
        
        return jsonify({
            'message': 'Case status updated',
            'case': case
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating case {case_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@case_bp.route('/<case_id>/notes', methods=['POST'])
@token_required
def add_note(current_user, case_id):
    """
    Add note to case
    Expected payload: {note}
    """
    try:
        data = request.get_json()
        note = data.get('note')
        
        if not note:
            return jsonify({'error': 'Note required'}), 400
        
        case = add_case_note(case_id, note, current_user['user_id'])
        
        return jsonify({
            'message': 'Note added successfully',
            'case': case
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding note to case {case_id}: {str(e)}")
        return jsonify({'error': 'Failed to add note'}), 500

@case_bp.route('/<case_id>/actions', methods=['POST'])
@token_required
def add_action(current_user, case_id):
    """
    Add action to case
    Expected payload: {action_type, description, amount (optional)}
    """
    try:
        data = request.get_json()
        action_type = data.get('action_type')
        description = data.get('description')
        amount = data.get('amount', 0)
        
        if not action_type or not description:
            return jsonify({'error': 'Action type and description required'}), 400
        
        case = add_case_action(
            case_id,
            action_type,
            description,
            current_user['user_id'],
            amount
        )
        
        return jsonify({
            'message': 'Action added successfully',
            'case': case
        }), 200
        
    except Exception as e:
        logger.error(f"Error adding action to case {case_id}: {str(e)}")
        return jsonify({'error': 'Failed to add action'}), 500

@case_bp.route('/<case_id>/escalate', methods=['POST'])
@token_required
def escalate_case_route(current_user, case_id):
    """
    Escalate case
    Expected payload: {reason}
    """
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        case = escalate_case(case_id, reason, current_user['user_id'])
        
        return jsonify({
            'message': 'Case escalated successfully',
            'case': case
        }), 200
        
    except Exception as e:
        logger.error(f"Error escalating case {case_id}: {str(e)}")
        return jsonify({'error': 'Failed to escalate case'}), 500

@case_bp.route('/<case_id>/events', methods=['GET'])
@token_required
def get_case_events(current_user, case_id):
    """Get events/history for a specific case"""
    try:
        from db.mongo import get_db
        db = get_db()
        
        events = list(db.events.find({'case_id': case_id}).sort('timestamp', -1))
        
        # Convert ObjectId to string and format dates
        for event in events:
            event['_id'] = str(event['_id'])
            if 'timestamp' in event:
                event['timestamp'] = event['timestamp'].isoformat()
        
        return jsonify(events), 200
        
    except Exception as e:
        logger.error(f"Error fetching events for case {case_id}: {str(e)}")
        return jsonify({'error': 'Failed to fetch case events'}), 500

@case_bp.route('/unassigned', methods=['GET'])
@token_required
def get_unassigned_cases(current_user):
    """Get all unassigned cases"""
    try:
        from db.mongo import get_db
        db = get_db()
        
        # Find cases without DCA assignment
        unassigned = list(db.cases.find({
            '$or': [
                {'assigned_dca': {'$exists': False}},
                {'assigned_dca': None},
                {'assigned_dca': ''},
                {'assigned_dca': 'Unassigned'}
            ],
            'status': {'$nin': ['resolved', 'closed']}
        }).sort('created_at', -1).limit(100))
        
        # Format response
        for case in unassigned:
            case['_id'] = str(case['_id'])
            for key in ['created_at', 'updated_at', 'sla_deadline']:
                if key in case and case[key]:
                    case[key] = case[key].isoformat()
        
        return jsonify({'cases': unassigned, 'count': len(unassigned)}), 200
        
    except Exception as e:
        logger.error(f"Error fetching unassigned cases: {str(e)}")
        return jsonify({'error': 'Failed to fetch unassigned cases'}), 500

@case_bp.route('/<case_id>/assign', methods=['POST'])
@token_required
def assign_case_route(current_user):
    """Manually assign a case to a DCA"""
    try:
        from db.mongo import get_db
        from datetime import datetime
        
        data = request.get_json()
        dca_id = data.get('dca_id')
        
        if not dca_id:
            return jsonify({'error': 'DCA ID required'}), 400
        
        db = get_db()
        
        # Verify DCA exists
        dca = db.dcas.find_one({'dca_id': dca_id})
        if not dca:
            return jsonify({'error': 'DCA not found'}), 404
        
        # Update case
        result = db.cases.update_one(
            {'case_id': case_id},
            {
                '$set': {
                    'assigned_dca': dca_id,
                    'status': 'assigned',
                    'assigned_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'metadata.assigned_by': current_user['user_id'],
                    'metadata.assignment_method': 'manual'
                }
            }
        )
        
        if result.modified_count == 0:
            return jsonify({'error': 'Case not found'}), 404
        
        # Create event
        db.events.insert_one({
            'case_id': case_id,
            'event_type': 'case_assigned',
            'description': f"Case manually assigned to {dca['name']}",
            'timestamp': datetime.utcnow(),
            'metadata': {
                'assigned_to': dca_id,
                'dca_name': dca['name'],
                'assigned_by': current_user['user_id'],
                'autonomous': False
            }
        })
        
        return jsonify({'message': 'Case assigned successfully', 'dca': dca['name']}), 200
        
    except Exception as e:
        logger.error(f"Error assigning case {case_id}: {str(e)}")
        return jsonify({'error': 'Failed to assign case'}), 500

@case_bp.route('/bulk-assign', methods=['POST'])
@token_required
def bulk_assign_cases(current_user):
    """Auto-assign all unassigned cases to DCAs"""
    try:
        from db.mongo import get_db
        from datetime import datetime
        
        db = get_db()
        
        # Get active DCAs
        dcas = list(db.dcas.find({'status': 'active'}))
        if not dcas:
            return jsonify({'error': 'No active DCAs available'}), 400
        
        # Get unassigned cases
        unassigned = list(db.cases.find({
            '$or': [
                {'assigned_dca': {'$exists': False}},
                {'assigned_dca': None},
                {'assigned_dca': ''},
                {'assigned_dca': 'Unassigned'}
            ],
            'status': {'$nin': ['resolved', 'closed']}
        }).sort('created_at', -1))
        
        if not unassigned:
            return jsonify({'message': 'No unassigned cases', 'assigned_count': 0}), 200
        
        # Round-robin assignment
        assigned_count = 0
        for i, case in enumerate(unassigned):
            dca = dcas[i % len(dcas)]
            
            db.cases.update_one(
                {'_id': case['_id']},
                {
                    '$set': {
                        'assigned_dca': dca['dca_id'],
                        'status': 'assigned',
                        'assigned_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'metadata.assigned_by': current_user['user_id'],
                        'metadata.assignment_method': 'bulk_auto'
                    }
                }
            )
            
            db.events.insert_one({
                'case_id': case['case_id'],
                'event_type': 'case_assigned',
                'description': f"Case auto-assigned to {dca['name']} (bulk)",
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'assigned_to': dca['dca_id'],
                    'dca_name': dca['name'],
                    'assigned_by': current_user['user_id'],
                    'autonomous': False,
                    'bulk_assignment': True
                }
            })
            
            assigned_count += 1
        
        return jsonify({
            'message': f'Successfully assigned {assigned_count} cases',
            'assigned_count': assigned_count,
            'dca_count': len(dcas)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in bulk assignment: {str(e)}")
        return jsonify({'error': 'Failed to bulk assign cases'}), 500
