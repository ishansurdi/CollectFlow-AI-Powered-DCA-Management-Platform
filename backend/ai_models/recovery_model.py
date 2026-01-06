import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score
import joblib
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RecoveryModel:
    """
    AI model for predicting debt recovery probability and expected amount
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.probability_model = None
        self.amount_model = None
        self.time_model = None
        self.model_path = './backend/ai_models/saved_models/'
        
        # Try to load existing models
        self.load_models()
    
    def prepare_features(self, data):
        """
        Prepare features for model input
        """
        if isinstance(data, dict):
            # Single prediction
            features = {
                'amount_overdue': data.get('amount_overdue', 0),
                'overdue_days': data.get('overdue_days', 0),
                'original_amount': data.get('original_amount', 0),
                'risk_score': data.get('risk_score', 50),
                'payment_history_length': data.get('payment_history_length', 0),
                'amount_ratio': data.get('amount_overdue', 0) / max(data.get('original_amount', 1), 1),
                'overdue_months': data.get('overdue_days', 0) / 30
            }
            return pd.DataFrame([features])
        else:
            # Batch prediction
            df = pd.DataFrame(data)
            df['amount_ratio'] = df['amount_overdue'] / df['original_amount'].clip(lower=1)
            df['overdue_months'] = df['overdue_days'] / 30
            return df
    
    def predict(self, features):
        """
        Predict recovery probability, expected amount, and timeline
        """
        try:
            feature_df = self.prepare_features(features)
            
            # If models not trained, use heuristics
            if self.probability_model is None:
                return self._heuristic_prediction(features)
            
            # Predict recovery probability
            recovery_prob = self.probability_model.predict_proba(feature_df)[0][1]
            
            # Predict expected recovery amount
            expected_amount = self.amount_model.predict(feature_df)[0]
            
            # Predict days to recover
            days_to_recover = int(self.time_model.predict(feature_df)[0])
            
            # Calculate confidence score based on feature quality
            confidence = self._calculate_confidence(features)
            
            return {
                'recovery_probability': float(recovery_prob),
                'expected_amount': float(max(0, expected_amount)),
                'days_to_recover': max(1, days_to_recover),
                'confidence_score': confidence
            }
            
        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}")
            return self._heuristic_prediction(features)
    
    def _heuristic_prediction(self, features):
        """
        Fallback heuristic-based prediction when ML model is not available
        """
        amount = features.get('amount_overdue', 0)
        days = features.get('overdue_days', 0)
        risk_score = features.get('risk_score', 50)
        
        # Simple rule-based probability
        if days < 30:
            base_prob = 0.8
        elif days < 60:
            base_prob = 0.6
        elif days < 90:
            base_prob = 0.4
        else:
            base_prob = 0.2
        
        # Adjust by risk score
        recovery_prob = base_prob * (1 - (risk_score / 200))
        recovery_prob = max(0.1, min(0.9, recovery_prob))
        
        # Expected amount
        expected_amount = amount * recovery_prob
        
        # Days to recover
        days_to_recover = min(90, days + 30)
        
        return {
            'recovery_probability': recovery_prob,
            'expected_amount': expected_amount,
            'days_to_recover': days_to_recover,
            'confidence_score': 0.5
        }
    
    def _calculate_confidence(self, features):
        """
        Calculate prediction confidence based on feature quality
        """
        confidence = 1.0
        
        # Reduce confidence if missing key features
        if features.get('risk_score') == 50:  # Default value
            confidence *= 0.9
        
        if features.get('payment_history_length', 0) == 0:
            confidence *= 0.85
        
        return round(confidence, 2)
    
    def train(self):
        """
        Train the models with historical data
        """
        try:
            logger.info("Training recovery prediction models...")
            
            # Load training data from database
            training_data = self._load_training_data()
            
            if len(training_data) < 100:
                logger.warning("Insufficient training data. Using default models.")
                return {'status': 'skipped', 'reason': 'insufficient_data'}
            
            # Prepare features and targets
            X = self.prepare_features(training_data)
            y_prob = training_data['recovered'].values
            y_amount = training_data['recovered_amount'].values
            y_time = training_data['recovery_days'].values
            
            # Split data
            X_train, X_test, y_prob_train, y_prob_test = train_test_split(
                X, y_prob, test_size=0.2, random_state=42
            )
            
            # Train probability model
            self.probability_model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            self.probability_model.fit(X_train, y_prob_train)
            prob_accuracy = accuracy_score(y_prob_test, self.probability_model.predict(X_test))
            
            # Train amount model
            self.amount_model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            self.amount_model.fit(X_train, y_amount[:len(X_train)])
            amount_mse = mean_squared_error(y_amount[len(X_train):], self.amount_model.predict(X_test))
            
            # Train time model
            self.time_model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            self.time_model.fit(X_train, y_time[:len(X_train)])
            time_mse = mean_squared_error(y_time[len(X_train):], self.time_model.predict(X_test))
            
            # Save models
            self.save_models()
            
            result = {
                'status': 'success',
                'version': self.version,
                'training_samples': len(training_data),
                'metrics': {
                    'probability_accuracy': float(prob_accuracy),
                    'amount_mse': float(amount_mse),
                    'time_mse': float(time_mse)
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Model training completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _load_training_data(self):
        """
        Load historical case data for training
        """
        try:
            from db.models import get_cases_collection, get_accounts_collection
            
            cases = get_cases_collection()
            accounts = get_accounts_collection()
            
            # Get resolved cases
            resolved_cases = list(cases.find({'status': 'resolved'}))
            
            training_data = []
            for case in resolved_cases:
                account = accounts.find_one({'account_number': case['account_number']})
                if not account:
                    continue
                
                # Calculate recovery days
                if case.get('resolved_at') and case.get('assigned_at'):
                    recovery_days = (case['resolved_at'] - case['assigned_at']).days
                else:
                    recovery_days = 30  # Default
                
                training_data.append({
                    'amount_overdue': account['amount_overdue'],
                    'overdue_days': account['overdue_days'],
                    'original_amount': account.get('original_amount', account['amount_overdue']),
                    'risk_score': 50,  # Would come from customer data
                    'payment_history_length': 0,
                    'recovered': 1,  # All resolved cases considered recovered
                    'recovered_amount': case['amount'],
                    'recovery_days': recovery_days
                })
            
            return pd.DataFrame(training_data)
            
        except Exception as e:
            logger.error(f"Error loading training data: {str(e)}")
            return pd.DataFrame()
    
    def save_models(self):
        """
        Save trained models to disk
        """
        try:
            os.makedirs(self.model_path, exist_ok=True)
            
            if self.probability_model:
                joblib.dump(self.probability_model, 
                          f"{self.model_path}recovery_probability_model.pkl")
            
            if self.amount_model:
                joblib.dump(self.amount_model,
                          f"{self.model_path}recovery_amount_model.pkl")
            
            if self.time_model:
                joblib.dump(self.time_model,
                          f"{self.model_path}recovery_time_model.pkl")
            
            # Save metadata
            metadata = {
                'version': self.version,
                'saved_at': datetime.utcnow().isoformat()
            }
            joblib.dump(metadata, f"{self.model_path}metadata.pkl")
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
    
    def load_models(self):
        """
        Load trained models from disk
        """
        try:
            prob_path = f"{self.model_path}recovery_probability_model.pkl"
            amount_path = f"{self.model_path}recovery_amount_model.pkl"
            time_path = f"{self.model_path}recovery_time_model.pkl"
            
            if os.path.exists(prob_path):
                self.probability_model = joblib.load(prob_path)
                self.amount_model = joblib.load(amount_path)
                self.time_model = joblib.load(time_path)
                logger.info("Models loaded successfully")
            else:
                logger.info("No saved models found. Using heuristic predictions.")
                
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
