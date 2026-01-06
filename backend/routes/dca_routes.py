from flask import Blueprint, request, jsonify
from utils.auth import token_required
from services.dca_service import (
    get_dca_portfolio,
    get_dca_performance,
    get_all_dcas,
    update_dca_capacity,
    get_dca_statistics
)
import logging

logger = logging.getLogger(__name__)

dca_bp = Blueprint('dca', __name__)

@dca_bp.route('/portfolio', methods=['GET'])
@token_required
def portfolio(current_user):
    """
    Get DCA portfolio (cases assigned to DCA)
    For DCA users and FedEx users (with dca_id parameter)
    """
    try:
        # DCA users see their own portfolio
        if current_user['role'].startswith('dca'):
            dca_id = current_user.get('dca_id')
            if not dca_id:
                logger.warning(f"DCA user {current_user.get('user_id')} has no dca_id assigned")
                return jsonify({
                    'dca_id': None,
                    'cases': [],
                    'count': 0,
                    'message': 'No DCA ID assigned to this user'
                }), 200
        # FedEx users can view any DCA's portfolio by providing dca_id
        elif current_user['role'].startswith('fedex'):
            dca_id = request.args.get('dca_id')
            if not dca_id:
                # Return empty if no DCA selected
                return jsonify({
                    'dca_id': None,
                    'cases': [],
                    'count': 0,
                    'message': 'Please select a DCA to view portfolio'
                }), 200
        else:
            logger.warning(f"Unauthorized access to DCA portfolio by user {current_user.get('user_id')}, role: {current_user.get('role')}")
            return jsonify({'error': 'Access denied'}), 403
        
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        portfolio = get_dca_portfolio(dca_id, status, priority)
        
        return jsonify({
            'dca_id': dca_id,
            'cases': portfolio,
            'count': len(portfolio)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching DCA portfolio: {str(e)}")
        return jsonify({'error': 'Failed to fetch portfolio'}), 500

@dca_bp.route('/performance', methods=['GET'])
@token_required
def performance(current_user):
    """
    Get DCA performance metrics
    """
    try:
        # Get DCA ID from user context or query parameter
        if current_user['role'].startswith('dca'):
            dca_id = current_user.get('dca_id')
        else:
            dca_id = request.args.get('dca_id')
        
        if not dca_id:
            logger.warning(f"No DCA ID found for user {current_user.get('user_id')}, role: {current_user.get('role')}")
            # Return empty performance data instead of error
            return jsonify({
                'dca_id': None,
                'name': 'Unknown',
                'status': 'inactive',
                'performance_score': 0,
                'capacity': 0,
                'current_cases': 0,
                'utilization': 0,
                'total_cases': 0,
                'active_cases': 0,
                'resolved_cases': 0,
                'recovery_rate': 0,
                'total_recovered': 0,
                'avg_recovery_time': 0
            }), 200
        
        performance_data = get_dca_performance(dca_id)
        
        return jsonify(performance_data), 200
        
    except ValueError as e:
        logger.error(f"DCA not found: {str(e)}")
        # Return empty performance data for non-existent DCA
        return jsonify({
            'dca_id': None,
            'name': 'Unknown',
            'status': 'inactive',
            'performance_score': 0,
            'capacity': 0,
            'current_cases': 0,
            'utilization': 0,
            'total_cases': 0,
            'active_cases': 0,
            'resolved_cases': 0,
            'recovery_rate': 0,
            'total_recovered': 0,
            'avg_recovery_time': 0
        }), 200
    except Exception as e:
        logger.error(f"Error fetching DCA performance: {str(e)}")
        return jsonify({'error': 'Failed to fetch performance'}), 500

@dca_bp.route('/list', methods=['GET'])
@token_required
def list_dcas(current_user):
    """
    Get list of all DCAs (FedEx users only)
    """
    try:
        if not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        status = request.args.get('status')
        dcas = get_all_dcas(status)
        
        return jsonify({
            'dcas': dcas,
            'count': len(dcas)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching DCAs: {str(e)}")
        return jsonify({'error': 'Failed to fetch DCAs'}), 500

@dca_bp.route('/<dca_id>/capacity', methods=['PUT'])
@token_required
def update_capacity(current_user, dca_id):
    """
    Update DCA capacity (FedEx admin only)
    Expected payload: {capacity}
    """
    try:
        if current_user['role'] != 'fedex_admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        capacity = data.get('capacity')
        
        if capacity is None:
            return jsonify({'error': 'Capacity required'}), 400
        
        dca = update_dca_capacity(dca_id, capacity)
        
        return jsonify({
            'message': 'Capacity updated successfully',
            'dca': dca
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating DCA capacity: {str(e)}")
        return jsonify({'error': 'Failed to update capacity'}), 500

@dca_bp.route('/<dca_id>/statistics', methods=['GET'])
@token_required
def statistics(current_user, dca_id):
    """
    Get detailed statistics for a DCA
    """
    try:
        # DCA users can only see their own stats
        if current_user['role'].startswith('dca'):
            if dca_id != current_user.get('dca_id'):
                return jsonify({'error': 'Unauthorized'}), 403
        elif not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        stats = get_dca_statistics(dca_id)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error fetching DCA statistics: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

@dca_bp.route('/actions', methods=['POST'])
@token_required
def record_action(current_user):
    """
    Record DCA action on a case
    Expected payload: {case_id, action_type, description, result (optional)}
    """
    try:
        if not current_user['role'].startswith('dca'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        case_id = data.get('case_id')
        action_type = data.get('action_type')
        description = data.get('description')
        result = data.get('result', {})
        
        if not all([case_id, action_type, description]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        from services.case_service import add_case_action
        case = add_case_action(
            case_id,
            action_type,
            description,
            current_user['user_id'],
            result.get('amount', 0)
        )
        
        return jsonify({
            'message': 'Action recorded successfully',
            'case': case
        }), 200
        
    except Exception as e:
        logger.error(f"Error recording action: {str(e)}")
        return jsonify({'error': 'Failed to record action'}), 500
