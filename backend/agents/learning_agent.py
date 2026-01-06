"""
Learning Agent - Continuous learning and model improvement
"""

from .base_agent import BaseAgent
from db.models import (
    get_cases_collection,
    get_predictions_collection,
    get_dcas_collection
)
from datetime import datetime, timedelta
import logging
import numpy as np

logger = logging.getLogger(__name__)


class LearningAgent(BaseAgent):
    """
    Autonomous agent that continuously learns from outcomes:
    - Evaluates prediction accuracy
    - Learns from case outcomes
    - Improves DCA performance assessment
    - Adapts routing strategies
    - Provides insights for model retraining
    """
    
    def __init__(self):
        super().__init__(name="LearningAgent")
        self.decision_threshold = 0.5  # Learning is always beneficial
        self.learning_window_days = 30
    
    def perceive(self, environment):
        """
        Perceive historical data for learning
        """
        try:
            cases_col = get_cases_collection()
            predictions_col = get_predictions_collection()
            dcas_col = get_dcas_collection()
            
            now = datetime.utcnow()
            window_start = now - timedelta(days=self.learning_window_days)
            
            # Get resolved cases with predictions
            resolved_cases = list(cases_col.find({
                'status': {'$in': ['resolved', 'written_off']},
                'resolved_at': {'$gte': window_start}
            }))
            
            # Get all predictions
            predictions = list(predictions_col.find({
                'created_at': {'$gte': window_start}
            }))
            
            # Get DCA performance data
            dcas = list(dcas_col.find({'status': 'active'}))
            
            perception = {
                'timestamp': now,
                'resolved_cases_count': len(resolved_cases),
                'predictions_count': len(predictions),
                'dcas_count': len(dcas),
                'resolved_cases': resolved_cases,
                'predictions': predictions,
                'dcas': dcas
            }
            
            logger.info(
                f"LearningAgent perception: {len(resolved_cases)} resolved cases, "
                f"{len(predictions)} predictions, {len(dcas)} DCAs"
            )
            
            return perception
            
        except Exception as e:
            logger.error(f"Error in learning agent perception: {str(e)}")
            return {'error': str(e)}
    
    def decide(self, perception):
        """
        Decide what to learn and what insights to generate
        """
        try:
            insights = []
            
            # Decision 1: Evaluate prediction accuracy
            prediction_accuracy = self._evaluate_predictions(
                perception.get('resolved_cases', []),
                perception.get('predictions', [])
            )
            
            if prediction_accuracy:
                insights.append({
                    'type': 'prediction_accuracy',
                    'data': prediction_accuracy,
                    'confidence': 0.9
                })
            
            # Decision 2: Analyze DCA performance
            dca_performance = self._analyze_dca_performance(
                perception.get('resolved_cases', []),
                perception.get('dcas', [])
            )
            
            if dca_performance:
                insights.append({
                    'type': 'dca_performance',
                    'data': dca_performance,
                    'confidence': 0.85
                })
            
            # Decision 3: Identify patterns and anomalies
            patterns = self._identify_patterns(perception.get('resolved_cases', []))
            
            if patterns:
                insights.append({
                    'type': 'patterns',
                    'data': patterns,
                    'confidence': 0.75
                })
            
            # Decision 4: Recommend model retraining
            if self._should_recommend_retraining(prediction_accuracy):
                insights.append({
                    'type': 'recommend_retraining',
                    'data': {
                        'reason': 'Prediction accuracy below threshold',
                        'current_accuracy': prediction_accuracy.get('accuracy', 0)
                    },
                    'confidence': 0.95
                })
            
            decision = {
                'timestamp': datetime.utcnow(),
                'insights': insights,
                'insight_count': len(insights),
                'confidence': sum(i.get('confidence', 0) for i in insights) / len(insights) if insights else 0,
                'threshold': self.decision_threshold
            }
            
            logger.info(
                f"LearningAgent decided on {len(insights)} insights "
                f"with avg confidence {decision['confidence']:.2f}"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in learning agent decision: {str(e)}")
            return {'insights': [], 'confidence': 0, 'error': str(e)}
    
    def act(self, decision):
        """
        Store insights and apply learnings
        """
        results = {
            'timestamp': datetime.utcnow(),
            'insights_stored': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        try:
            for insight in decision.get('insights', []):
                try:
                    result = self._store_insight(insight)
                    results['insights_stored'].append(result)
                    if result.get('success'):
                        results['success_count'] += 1
                    else:
                        results['failure_count'] += 1
                        
                except Exception as e:
                    logger.error(f"Error storing insight: {str(e)}")
                    results['failure_count'] += 1
            
            results['success'] = results['success_count'] > 0
            results['action'] = 'learning_cycle'
            results['outcome'] = f"{results['success_count']} insights stored"
            
            logger.info(
                f"LearningAgent stored {results['success_count']} insights"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in learning agent action: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': 'learning_cycle',
                'outcome': 'failed'
            }
    
    # Helper methods
    
    def _evaluate_predictions(self, resolved_cases, predictions):
        """Evaluate prediction accuracy against actual outcomes"""
        try:
            if not resolved_cases or not predictions:
                return None
            
            # Match predictions with outcomes
            matched_predictions = []
            
            for case in resolved_cases:
                # Find prediction for this case
                prediction = next(
                    (p for p in predictions if p.get('case_id') == case['case_id']),
                    None
                )
                
                if prediction:
                    actual_recovered = case.get('recovered_amount', 0)
                    predicted_amount = prediction.get('expected_amount', 0)
                    
                    if case['status'] == 'resolved':
                        actual_probability = 1.0
                    else:
                        actual_probability = 0.0
                    
                    predicted_probability = prediction.get('recovery_probability', 0.5)
                    
                    matched_predictions.append({
                        'case_id': case['case_id'],
                        'predicted_probability': predicted_probability,
                        'actual_probability': actual_probability,
                        'predicted_amount': predicted_amount,
                        'actual_amount': actual_recovered,
                        'probability_error': abs(predicted_probability - actual_probability),
                        'amount_error': abs(predicted_amount - actual_recovered)
                    })
            
            if not matched_predictions:
                return None
            
            # Calculate metrics
            avg_probability_error = np.mean([p['probability_error'] for p in matched_predictions])
            avg_amount_error = np.mean([p['amount_error'] for p in matched_predictions])
            
            # Calculate accuracy (predictions within 20% threshold)
            accurate_predictions = sum(
                1 for p in matched_predictions if p['probability_error'] < 0.2
            )
            accuracy = accurate_predictions / len(matched_predictions)
            
            return {
                'total_predictions': len(matched_predictions),
                'accuracy': accuracy,
                'avg_probability_error': avg_probability_error,
                'avg_amount_error': avg_amount_error,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating predictions: {str(e)}")
            return None
    
    def _analyze_dca_performance(self, resolved_cases, dcas):
        """Analyze DCA performance from outcomes"""
        try:
            dca_stats = {}
            
            for case in resolved_cases:
                dca_id = case.get('assigned_dca')
                if not dca_id:
                    continue
                
                if dca_id not in dca_stats:
                    dca_stats[dca_id] = {
                        'total_cases': 0,
                        'resolved_cases': 0,
                        'total_recovered': 0,
                        'total_expected': 0,
                        'avg_resolution_days': []
                    }
                
                stats = dca_stats[dca_id]
                stats['total_cases'] += 1
                
                if case['status'] == 'resolved':
                    stats['resolved_cases'] += 1
                    stats['total_recovered'] += case.get('recovered_amount', 0)
                    
                    if case.get('resolved_at') and case.get('assigned_at'):
                        resolution_days = (case['resolved_at'] - case['assigned_at']).days
                        stats['avg_resolution_days'].append(resolution_days)
                
                stats['total_expected'] += case.get('amount', 0)
            
            # Calculate performance metrics for each DCA
            performance_results = []
            
            for dca_id, stats in dca_stats.items():
                if stats['total_cases'] > 0:
                    resolution_rate = stats['resolved_cases'] / stats['total_cases']
                    recovery_rate = (
                        stats['total_recovered'] / stats['total_expected'] 
                        if stats['total_expected'] > 0 else 0
                    )
                    avg_days = (
                        np.mean(stats['avg_resolution_days']) 
                        if stats['avg_resolution_days'] else 0
                    )
                    
                    # Calculate performance score (0-100)
                    performance_score = (
                        resolution_rate * 40 +
                        recovery_rate * 40 +
                        max(0, 100 - avg_days * 2) * 0.2
                    )
                    
                    performance_results.append({
                        'dca_id': dca_id,
                        'resolution_rate': resolution_rate,
                        'recovery_rate': recovery_rate,
                        'avg_resolution_days': avg_days,
                        'performance_score': performance_score,
                        'total_cases': stats['total_cases']
                    })
            
            # Update DCA performance scores in database
            if performance_results:
                self._update_dca_scores(performance_results)
            
            return {
                'dcas_analyzed': len(performance_results),
                'results': performance_results,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing DCA performance: {str(e)}")
            return None
    
    def _identify_patterns(self, resolved_cases):
        """Identify patterns in case outcomes"""
        try:
            if len(resolved_cases) < 10:
                return None
            
            patterns = {
                'by_priority': {},
                'by_amount_range': {},
                'by_overdue_days': {}
            }
            
            for case in resolved_cases:
                # Pattern by priority
                priority = case.get('priority', 'unknown')
                if priority not in patterns['by_priority']:
                    patterns['by_priority'][priority] = {'total': 0, 'resolved': 0}
                patterns['by_priority'][priority]['total'] += 1
                if case['status'] == 'resolved':
                    patterns['by_priority'][priority]['resolved'] += 1
                
                # Pattern by amount
                amount = case.get('amount', 0)
                if amount < 5000:
                    range_key = 'under_5k'
                elif amount < 10000:
                    range_key = '5k_10k'
                elif amount < 25000:
                    range_key = '10k_25k'
                else:
                    range_key = 'over_25k'
                
                if range_key not in patterns['by_amount_range']:
                    patterns['by_amount_range'][range_key] = {'total': 0, 'resolved': 0}
                patterns['by_amount_range'][range_key]['total'] += 1
                if case['status'] == 'resolved':
                    patterns['by_amount_range'][range_key]['resolved'] += 1
            
            # Calculate success rates for each pattern
            for category in patterns:
                for key in patterns[category]:
                    total = patterns[category][key]['total']
                    resolved = patterns[category][key]['resolved']
                    patterns[category][key]['success_rate'] = resolved / total if total > 0 else 0
            
            return {
                'patterns': patterns,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error identifying patterns: {str(e)}")
            return None
    
    def _should_recommend_retraining(self, prediction_accuracy):
        """Determine if model retraining should be recommended"""
        if not prediction_accuracy:
            return False
        
        # Recommend retraining if accuracy is below 70%
        return prediction_accuracy.get('accuracy', 1.0) < 0.7
    
    def _store_insight(self, insight):
        """Store insight in database"""
        try:
            from db.models import get_insights_collection
            
            insights_col = get_insights_collection()
            
            insight_doc = {
                'insight_id': f"INS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                'type': insight['type'],
                'data': insight['data'],
                'confidence': insight['confidence'],
                'agent': self.name,
                'created_at': datetime.utcnow()
            }
            
            insights_col.insert_one(insight_doc)
            
            logger.info(f"Stored insight: {insight['type']}")
            
            return {
                'insight_type': insight['type'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to store insight: {str(e)}")
            return {
                'insight_type': insight['type'],
                'success': False,
                'error': str(e)
            }
    
    def _update_dca_scores(self, performance_results):
        """Update DCA performance scores in database"""
        try:
            dcas_col = get_dcas_collection()
            
            for result in performance_results:
                dcas_col.update_one(
                    {'dca_id': result['dca_id']},
                    {
                        '$set': {
                            'performance_score': result['performance_score'],
                            'resolution_rate': result['resolution_rate'],
                            'recovery_rate': result['recovery_rate'],
                            'avg_resolution_days': result['avg_resolution_days'],
                            'performance_updated_at': datetime.utcnow()
                        }
                    }
                )
            
            logger.info(f"Updated performance scores for {len(performance_results)} DCAs")
            
        except Exception as e:
            logger.error(f"Failed to update DCA scores: {str(e)}")
