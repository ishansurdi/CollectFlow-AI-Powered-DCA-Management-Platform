import numpy as np
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RoutingModel:
    """
    AI model for routing cases to the best DCA
    """
    
    def __init__(self):
        self.version = "1.0.0"
    
    def recommend(self, case_features, available_dcas):
        """
        Recommend the best DCA for a case
        """
        try:
            if not available_dcas:
                raise ValueError("No available DCAs")
            
            # Score each DCA
            dca_scores = []
            for dca in available_dcas:
                score = self._score_dca(case_features, dca)
                dca_scores.append({
                    'dca_id': dca['dca_id'],
                    'name': dca['name'],
                    'score': score,
                    'performance_score': dca.get('performance_score', 0),
                    'current_cases': dca.get('current_cases', 0),
                    'capacity': dca['capacity'],
                    'recovery_rate': dca.get('recovery_rate', 0)
                })
            
            # Sort by score descending
            dca_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Get top 3 recommendations
            top_recommendations = dca_scores[:3]
            
            result = {
                'recommended_dca': top_recommendations[0]['dca_id'],
                'recommended_name': top_recommendations[0]['name'],
                'score': top_recommendations[0]['score'],
                'alternatives': [
                    {
                        'dca_id': rec['dca_id'],
                        'name': rec['name'],
                        'score': rec['score']
                    }
                    for rec in top_recommendations[1:]
                ],
                'reasoning': self._generate_reasoning(case_features, top_recommendations[0])
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in DCA recommendation: {str(e)}")
            raise
    
    def _score_dca(self, case_features, dca):
        """
        Score a DCA for a specific case
        """
        score = 0
        
        # Factor 1: Performance score (0-100) - weight 40%
        performance_score = dca.get('performance_score', 50)
        score += performance_score * 0.4
        
        # Factor 2: Availability (capacity utilization) - weight 30%
        capacity = dca['capacity']
        current_cases = dca.get('current_cases', 0)
        utilization = current_cases / capacity if capacity > 0 else 1.0
        availability_score = (1 - utilization) * 100
        score += availability_score * 0.3
        
        # Factor 3: Recovery rate - weight 20%
        recovery_rate = dca.get('recovery_rate', 0)
        score += recovery_rate * 0.2
        
        # Factor 4: Specialization match - weight 10%
        case_priority = case_features.get('priority', 'medium')
        specialization = dca.get('specialization', [])
        
        specialization_score = 0
        if case_priority == 'critical' and 'high_value' in specialization:
            specialization_score = 100
        elif case_priority in ['high', 'critical'] and 'commercial' in specialization:
            specialization_score = 80
        elif 'general' in specialization:
            specialization_score = 60
        else:
            specialization_score = 40
        
        score += specialization_score * 0.1
        
        return round(score, 2)
    
    def _generate_reasoning(self, case_features, selected_dca):
        """
        Generate human-readable reasoning for the recommendation
        """
        reasons = []
        
        if selected_dca['performance_score'] >= 80:
            reasons.append("High performance score")
        
        utilization = selected_dca['current_cases'] / selected_dca['capacity']
        if utilization < 0.7:
            reasons.append("Good availability")
        
        if selected_dca['recovery_rate'] >= 70:
            reasons.append("Strong recovery rate")
        
        if not reasons:
            reasons.append("Best available option")
        
        return ", ".join(reasons)
    
    def train(self):
        """
        Train routing model with historical assignment data
        """
        try:
            logger.info("Training routing model...")
            
            # For MVP, we use rule-based routing
            # In production, this would train on historical assignment success data
            
            result = {
                'status': 'success',
                'version': self.version,
                'method': 'rule_based',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("Routing model training completed (rule-based)")
            return result
            
        except Exception as e:
            logger.error(f"Error training routing model: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def batch_recommend(self, cases, available_dcas):
        """
        Recommend DCAs for multiple cases at once
        """
        try:
            recommendations = []
            
            for case in cases:
                case_features = {
                    'amount': case.get('amount', 0),
                    'overdue_days': case.get('overdue_days', 0),
                    'priority': case.get('priority', 'medium')
                }
                
                rec = self.recommend(case_features, available_dcas)
                recommendations.append({
                    'case_id': case.get('case_id'),
                    'recommendation': rec
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in batch recommendation: {str(e)}")
            raise
    
    def optimize_workload(self, dcas):
        """
        Suggest workload rebalancing across DCAs
        """
        try:
            recommendations = []
            
            # Calculate average utilization
            total_utilization = sum(
                dca['current_cases'] / dca['capacity']
                for dca in dcas if dca['capacity'] > 0
            )
            avg_utilization = total_utilization / len(dcas) if dcas else 0
            
            for dca in dcas:
                utilization = dca['current_cases'] / dca['capacity'] if dca['capacity'] > 0 else 0
                
                if utilization > avg_utilization * 1.2:
                    recommendations.append({
                        'dca_id': dca['dca_id'],
                        'name': dca['name'],
                        'issue': 'overutilized',
                        'utilization': round(utilization * 100, 2),
                        'suggestion': 'Consider reassigning some cases or increasing capacity'
                    })
                elif utilization < avg_utilization * 0.5 and dca['status'] == 'active':
                    recommendations.append({
                        'dca_id': dca['dca_id'],
                        'name': dca['name'],
                        'issue': 'underutilized',
                        'utilization': round(utilization * 100, 2),
                        'suggestion': 'Can handle more cases'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in workload optimization: {str(e)}")
            raise
