from flask import Blueprint, request, jsonify
from utils.auth import token_required
from services.ai_service import (
    predict_recovery,
    score_accounts,
    recommend_dca,
    retrain_models
)
import logging

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/predict-recovery', methods=['POST'])
@token_required
def predict_recovery_route(current_user):
    """
    Get AI prediction for recovery probability
    Expected payload: {account_number} or {case_id}
    """
    try:
        # Allow both FedEx and DCA users to access AI predictions
        
        data = request.get_json()
        account_number = data.get('account_number')
        case_id = data.get('case_id')
        
        if not account_number and not case_id:
            return jsonify({'error': 'Account number or case ID required'}), 400
        
        prediction = predict_recovery(account_number, case_id)
        
        return jsonify(prediction), 200
        
    except Exception as e:
        logger.error(f"Error predicting recovery: {str(e)}")
        return jsonify({'error': 'Prediction failed'}), 500

@ai_bp.route('/score-accounts', methods=['POST'])
@token_required
def score_accounts_route(current_user):
    """
    Score multiple accounts for prioritization
    Expected payload: {account_numbers: [list of account numbers]}
    """
    try:
        if not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        account_numbers = data.get('account_numbers', [])
        
        if not account_numbers:
            return jsonify({'error': 'Account numbers required'}), 400
        
        scores = score_accounts(account_numbers)
        
        return jsonify({
            'scores': scores,
            'count': len(scores)
        }), 200
        
    except Exception as e:
        logger.error(f"Error scoring accounts: {str(e)}")
        return jsonify({'error': 'Scoring failed'}), 500

@ai_bp.route('/recommend-dca', methods=['POST'])
@token_required
def recommend_dca_route(current_user):
    """
    Get AI recommendation for best DCA for a case
    Expected payload: {case_id} or {account_number}
    """
    try:
        if not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        case_id = data.get('case_id')
        account_number = data.get('account_number')
        
        if not case_id and not account_number:
            return jsonify({'error': 'Case ID or account number required'}), 400
        
        recommendation = recommend_dca(case_id, account_number)
        
        return jsonify(recommendation), 200
        
    except Exception as e:
        logger.error(f"Error recommending DCA: {str(e)}")
        return jsonify({'error': 'Recommendation failed'}), 500

@ai_bp.route('/retrain', methods=['POST'])
@token_required
def retrain_models_route(current_user):
    """
    Trigger model retraining (Admin only)
    """
    try:
        if current_user['role'] != 'fedex_admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        result = retrain_models()
        
        return jsonify({
            'message': 'Model retraining initiated',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error retraining models: {str(e)}")
        return jsonify({'error': 'Retraining failed'}), 500

@ai_bp.route('/batch-predict', methods=['POST'])
@token_required
def batch_predict(current_user):
    """
    Batch prediction for multiple accounts
    Expected payload: {account_numbers: [list]}
    """
    try:
        if not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        account_numbers = data.get('account_numbers', [])
        
        if not account_numbers:
            return jsonify({'error': 'Account numbers required'}), 400
        
        predictions = []
        for account_number in account_numbers:
            try:
                pred = predict_recovery(account_number, None)
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"Failed to predict for {account_number}: {str(e)}")
                predictions.append({
                    'account_number': account_number,
                    'error': str(e)
                })
        
        return jsonify({
            'predictions': predictions,
            'count': len(predictions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch prediction: {str(e)}")
        return jsonify({'error': 'Batch prediction failed'}), 500
