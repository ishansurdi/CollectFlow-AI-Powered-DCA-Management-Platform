from db.models import (
    get_accounts_collection,
    get_cases_collection,
    get_dcas_collection,
    get_predictions_collection
)
from ai_models.recovery_model import RecoveryModel
from ai_models.routing_model import RoutingModel
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

# Initialize models
recovery_model = RecoveryModel()
routing_model = RoutingModel()

def predict_recovery(account_number, case_id):
    """
    Predict recovery probability and expected amount for an account
    """
    try:
        accounts = get_accounts_collection()
        
        # Get account data
        if account_number:
            account = accounts.find_one({'account_number': account_number})
        elif case_id:
            cases = get_cases_collection()
            case = cases.find_one({'case_id': case_id})
            if not case:
                raise ValueError(f"Case {case_id} not found")
            account = accounts.find_one({'account_number': case['account_number']})
        else:
            raise ValueError("Either account_number or case_id required")
        
        if not account:
            raise ValueError("Account not found")
        
        # Prepare features
        features = {
            'amount_overdue': account['amount_overdue'],
            'overdue_days': account['overdue_days'],
            'original_amount': account.get('original_amount', account['amount_overdue']),
        }
        
        # Get customer data for additional features
        from db.models import get_customers_collection
        customers = get_customers_collection()
        customer = customers.find_one({'customer_id': account['customer_id']})
        if customer:
            features['risk_score'] = customer.get('risk_score', 50)
            features['payment_history_length'] = len(customer.get('payment_history', []))
        
        # Make prediction
        prediction = recovery_model.predict(features)
        
        # Store prediction
        prediction_id = f"PRED-{uuid.uuid4().hex[:8].upper()}"
        prediction_data = {
            'prediction_id': prediction_id,
            'account_number': account['account_number'],
            'case_id': case_id,
            'recovery_probability': prediction['recovery_probability'],
            'expected_amount': prediction['expected_amount'],
            'days_to_recover': prediction['days_to_recover'],
            'confidence_score': prediction['confidence_score'],
            'model_version': recovery_model.version,
            'created_at': datetime.utcnow(),
            'features_used': features
        }
        
        predictions = get_predictions_collection()
        predictions.insert_one(prediction_data)
        
        logger.info(f"Prediction made for account {account['account_number']}")
        
        return prediction
        
    except Exception as e:
        logger.error(f"Error predicting recovery: {str(e)}")
        raise

def score_accounts(account_numbers):
    """
    Score multiple accounts for prioritization
    """
    try:
        accounts = get_accounts_collection()
        
        scores = []
        for account_number in account_numbers:
            account = accounts.find_one({'account_number': account_number})
            if not account:
                continue
            
            try:
                prediction = predict_recovery(account_number, None)
                
                # Calculate priority score
                score = (
                    account['amount_overdue'] * 0.3 +
                    account['overdue_days'] * 0.2 +
                    prediction['recovery_probability'] * 100 * 0.5
                )
                
                scores.append({
                    'account_number': account_number,
                    'score': round(score, 2),
                    'amount_overdue': account['amount_overdue'],
                    'overdue_days': account['overdue_days'],
                    'recovery_probability': prediction['recovery_probability']
                })
            except Exception as e:
                logger.warning(f"Failed to score account {account_number}: {str(e)}")
        
        # Sort by score descending
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        return scores
        
    except Exception as e:
        logger.error(f"Error scoring accounts: {str(e)}")
        raise

def recommend_dca(case_id, account_number):
    """
    Recommend best DCA for a case using AI routing
    """
    try:
        cases = get_cases_collection()
        accounts = get_accounts_collection()
        dcas = get_dcas_collection()
        
        # Get case/account data
        if case_id:
            case = cases.find_one({'case_id': case_id})
            if not case:
                raise ValueError(f"Case {case_id} not found")
            account = accounts.find_one({'account_number': case['account_number']})
        elif account_number:
            account = accounts.find_one({'account_number': account_number})
        else:
            raise ValueError("Either case_id or account_number required")
        
        if not account:
            raise ValueError("Account not found")
        
        # Get available DCAs
        available_dcas = list(dcas.find({
            'status': 'active',
            '$expr': {'$lt': ['$current_cases', '$capacity']}
        }))
        
        if not available_dcas:
            raise ValueError("No available DCAs")
        
        # Prepare case features
        case_features = {
            'amount': account['amount_overdue'],
            'overdue_days': account['overdue_days'],
            'priority': case.get('priority', 'medium') if case_id else 'medium'
        }
        
        # Get DCA recommendations
        recommendation = routing_model.recommend(case_features, available_dcas)
        
        logger.info(f"DCA recommendation: {recommendation['recommended_dca']}")
        
        return recommendation
        
    except Exception as e:
        logger.error(f"Error recommending DCA: {str(e)}")
        raise

def retrain_models():
    """
    Retrain AI models with latest data
    """
    try:
        logger.info("Starting model retraining...")
        
        # Retrain recovery model
        recovery_result = recovery_model.train()
        
        # Retrain routing model
        routing_result = routing_model.train()
        
        result = {
            'recovery_model': recovery_result,
            'routing_model': routing_result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("Model retraining completed successfully")
        
        return result
        
    except Exception as e:
        logger.error(f"Error retraining models: {str(e)}")
        raise
