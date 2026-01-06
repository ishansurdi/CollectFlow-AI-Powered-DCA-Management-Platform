"""
Recovery Optimization Agent - Maximizes recovery outcomes
"""

from .base_agent import BaseAgent
from db.models import get_cases_collection, get_accounts_collection, create_event
from services.ai_service import predict_recovery
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


class RecoveryOptimizationAgent(BaseAgent):
    """
    Autonomous agent that optimizes recovery strategies:
    - Identifies high-value recovery opportunities
    - Recommends settlement strategies
    - Detects payment patterns
    - Suggests proactive interventions
    - Optimizes collection timing
    """
    
    def __init__(self):
        super().__init__(name="RecoveryOptimizationAgent")
        self.decision_threshold = 0.65
    
    def perceive(self, environment):
        """
        Perceive recovery opportunities and patterns
        """
        try:
            cases_col = get_cases_collection()
            accounts_col = get_accounts_collection()
            
            # Find cases with high recovery probability but stuck
            high_potential_cases = list(cases_col.find({
                'status': 'assigned',
                'recovery_probability': {'$gte': 0.7},
                'assigned_at': {'$lt': datetime.utcnow() - timedelta(days=3)}
            }))
            
            # Find cases that might benefit from settlement
            settlement_candidates = list(cases_col.find({
                'status': 'assigned',
                'recovery_probability': {'$lt': 0.5, '$gte': 0.2},
                'amount': {'$gte': 5000}
            }))
            
            # Find cases with declining probability
            declining_cases = list(cases_col.find({
                'status': 'assigned',
                'probability_trend': 'declining'
            }))
            
            perception = {
                'timestamp': datetime.utcnow(),
                'high_potential_count': len(high_potential_cases),
                'settlement_candidates_count': len(settlement_candidates),
                'declining_cases_count': len(declining_cases),
                'high_potential_cases': high_potential_cases,
                'settlement_candidates': settlement_candidates,
                'declining_cases': declining_cases
            }
            
            logger.info(
                f"RecoveryAgent perception: {len(high_potential_cases)} high potential, "
                f"{len(settlement_candidates)} settlement candidates"
            )
            
            return perception
            
        except Exception as e:
            logger.error(f"Error in recovery agent perception: {str(e)}")
            return {'error': str(e)}
    
    def decide(self, perception):
        """
        Decide on recovery optimization strategies
        """
        try:
            actions = []
            
            # Decision 1: Prioritize high-potential cases
            for case in perception.get('high_potential_cases', []):
                action = self._decide_high_potential_action(case)
                if action:
                    actions.append(action)
            
            # Decision 2: Recommend settlements
            for case in perception.get('settlement_candidates', []):
                settlement = self._calculate_settlement_offer(case)
                if settlement:
                    actions.append({
                        'type': 'recommend_settlement',
                        'case': case,
                        'settlement_offer': settlement,
                        'confidence': settlement['confidence']
                    })
            
            # Decision 3: Intervention for declining cases
            for case in perception.get('declining_cases', []):
                actions.append({
                    'type': 'intervene_declining',
                    'case': case,
                    'confidence': 0.75
                })
            
            # Sort by potential value and confidence
            actions.sort(
                key=lambda x: (
                    x.get('potential_value', 0) * x.get('confidence', 0)
                ),
                reverse=True
            )
            
            decision = {
                'timestamp': datetime.utcnow(),
                'actions': actions,
                'action_count': len(actions),
                'confidence': sum(a.get('confidence', 0) for a in actions) / len(actions) if actions else 0,
                'threshold': self.decision_threshold
            }
            
            logger.info(
                f"RecoveryAgent decided on {len(actions)} actions "
                f"with avg confidence {decision['confidence']:.2f}"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in recovery agent decision: {str(e)}")
            return {'actions': [], 'confidence': 0, 'error': str(e)}
    
    def act(self, decision):
        """
        Execute recovery optimization actions
        """
        results = {
            'timestamp': datetime.utcnow(),
            'actions_executed': [],
            'success_count': 0,
            'failure_count': 0,
            'total_potential_value': 0
        }
        
        try:
            for action in decision.get('actions', []):
                if action.get('confidence', 0) < self.decision_threshold:
                    continue
                
                try:
                    if action['type'] == 'prioritize_case':
                        result = self._prioritize_case_action(action)
                    elif action['type'] == 'recommend_settlement':
                        result = self._recommend_settlement_action(action)
                    elif action['type'] == 'intervene_declining':
                        result = self._intervene_declining_action(action)
                    else:
                        continue
                    
                    results['actions_executed'].append(result)
                    if result.get('success'):
                        results['success_count'] += 1
                        results['total_potential_value'] += result.get('potential_value', 0)
                    else:
                        results['failure_count'] += 1
                        
                except Exception as e:
                    logger.error(f"Error executing recovery action {action['type']}: {str(e)}")
                    results['failure_count'] += 1
            
            results['success'] = results['success_count'] > 0
            results['action'] = 'recovery_optimization_cycle'
            results['outcome'] = (
                f"{results['success_count']} successes, "
                f"${results['total_potential_value']:.2f} potential value"
            )
            
            logger.info(
                f"RecoveryAgent executed {len(results['actions_executed'])} actions - "
                f"${results['total_potential_value']:.2f} potential value"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in recovery agent action: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': 'recovery_optimization_cycle',
                'outcome': 'failed'
            }
    
    # Helper methods
    
    def _decide_high_potential_action(self, case):
        """Decide action for high-potential cases"""
        try:
            recovery_prob = case.get('recovery_probability', 0.5)
            amount = case.get('amount', 0)
            
            if recovery_prob >= 0.8 and amount >= 10000:
                return {
                    'type': 'prioritize_case',
                    'case': case,
                    'confidence': recovery_prob,
                    'potential_value': amount * recovery_prob,
                    'proposed_changes': {
                        'priority': 'high',
                        'recommended_action': 'Immediate contact with payment plan',
                        'reason': f'High recovery probability ({recovery_prob:.0%}) with significant value (${amount:,.2f})'
                    }
                }
            return None
        except Exception as e:
            logger.error(f"Error deciding high potential action: {str(e)}")
            return None
    
    def _old_decide_high_potential_action(self, case):
        """Decide action for high-potential case"""
        # Check if case needs prioritization
        if case.get('priority') != 'critical':
            potential_value = case.get('amount', 0) * case.get('recovery_probability', 0.5)
            
            return {
                'type': 'prioritize_case',
                'case': case,
                'reason': 'High recovery probability with significant value',
                'potential_value': potential_value,
                'confidence': case.get('recovery_probability', 0.5)
            }
        
        return None
    
    def _calculate_settlement_offer(self, case):
        """Calculate optimal settlement offer"""
        try:
            amount = case.get('amount', 0)
            recovery_prob = case.get('recovery_probability', 0.3)
            
            # Settlement strategy: offer 60-80% based on probability
            if recovery_prob < 0.3:
                settlement_percentage = 0.60
                confidence = 0.7
            elif recovery_prob < 0.4:
                settlement_percentage = 0.70
                confidence = 0.75
            else:
                settlement_percentage = 0.75
                confidence = 0.8
            
            settlement_amount = amount * settlement_percentage
            expected_value = settlement_amount * confidence
            
            # Only recommend if settlement has good expected value
            if expected_value > amount * 0.5:
                return {
                    'settlement_amount': settlement_amount,
                    'settlement_percentage': settlement_percentage * 100,
                    'expected_value': expected_value,
                    'confidence': confidence,
                    'reasoning': f'Settlement at {settlement_percentage*100:.0f}% likely to recover more than continuing'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calculating settlement: {str(e)}")
            return None
    
    def _prioritize_case_action(self, action):
        """Create a pending recommendation for case prioritization"""
        try:
            case = action['case']
            proposed = action.get('proposed_changes', {})
            
            # Create event with pending approval
            event = create_event({
                'event_type': 'recovery_optimization',
                'case_id': case.get('case_id'),
                'description': f"High-priority recovery opportunity identified: {proposed.get('reason', 'High recovery potential')}",
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'agent_name': self.name,
                    'autonomous': True,
                    'confidence': action.get('confidence', 0.7),
                    'action_type': 'prioritize_case',
                    'status': 'pending_approval',
                    'proposed_changes': proposed,
                    'current_values': {
                        'priority': case.get('priority', 'medium'),
                        'status': case.get('status', 'assigned'),
                        'recovery_probability': case.get('recovery_probability', 0)
                    },
                    'recovery_probability': case.get('recovery_probability', 0),
                    'amount_due': case.get('amount', 0),
                    'decision': f"Recommend priority upgrade to {proposed.get('priority', 'high')}",
                    'reasoning': proposed.get('reason', ''),
                    'potential_value': action.get('potential_value', 0)
                }
            })
            
            return {
                'success': True,
                'action_type': 'prioritize_case',
                'case_id': case.get('case_id'),
                'event_id': event,
                'potential_value': action.get('potential_value', 0),
                'status': 'pending_approval'
            }
        except Exception as e:
            logger.error(f"Error creating prioritize case recommendation: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _old_prioritize_case_action(self, action):
        """Prioritize a high-potential case"""
        try:
            cases_col = get_cases_collection()
            case = action['case']
            
            # Add priority flag and recommendation
            cases_col.update_one(
                {'case_id': case['case_id']},
                {
                    '$set': {
                        'optimization_priority': 'high',
                        'optimization_reason': action['reason'],
                        'potential_value': action['potential_value'],
                        'optimized_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Create event
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'recovery_optimization',
                'description': f"High-priority recovery opportunity identified: {action['reason']}",
                'user_id': self.agent_id,
                'metadata': {
                    'potential_value': action['potential_value'],
                    'autonomous': True
                }
            })
            
            logger.info(
                f"Agent prioritized case {case['case_id']} "
                f"with potential value ${action['potential_value']:.2f}"
            )
            
            return {
                'action_type': 'prioritize_case',
                'case_id': case['case_id'],
                'potential_value': action['potential_value'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to prioritize case: {str(e)}")
            return {
                'action_type': 'prioritize_case',
                'success': False,
                'error': str(e)
            }
    
    def _recommend_settlement_action(self, action):
        """Recommend settlement offer"""
        try:
            cases_col = get_cases_collection()
            case = action['case']
            settlement = action['settlement_offer']
            
            # Store settlement recommendation
            cases_col.update_one(
                {'case_id': case['case_id']},
                {
                    '$set': {
                        'settlement_recommendation': settlement,
                        'settlement_recommended_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Create event
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'settlement_recommended',
                'description': (
                    f"Settlement recommended: ${settlement['settlement_amount']:.2f} "
                    f"({settlement['settlement_percentage']:.0f}%) - {settlement['reasoning']}"
                ),
                'user_id': self.agent_id,
                'metadata': {
                    'settlement_amount': settlement['settlement_amount'],
                    'settlement_percentage': settlement['settlement_percentage'],
                    'expected_value': settlement['expected_value'],
                    'autonomous': True
                }
            })
            
            logger.info(
                f"Agent recommended settlement for case {case['case_id']}: "
                f"${settlement['settlement_amount']:.2f}"
            )
            
            return {
                'action_type': 'recommend_settlement',
                'case_id': case['case_id'],
                'settlement_amount': settlement['settlement_amount'],
                'potential_value': settlement['expected_value'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to recommend settlement: {str(e)}")
            return {
                'action_type': 'recommend_settlement',
                'success': False,
                'error': str(e)
            }
    
    def _intervene_declining_action(self, action):
        """Intervene on declining case"""
        try:
            case = action['case']
            
            # Create intervention recommendation event
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'intervention_recommended',
                'description': "Declining recovery probability detected - immediate intervention recommended",
                'user_id': self.agent_id,
                'metadata': {
                    'intervention_type': 'declining_probability',
                    'autonomous': True
                }
            })
            
            logger.warning(
                f"Agent recommended intervention for declining case {case['case_id']}"
            )
            
            return {
                'action_type': 'intervene_declining',
                'case_id': case['case_id'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to intervene: {str(e)}")
            return {
                'action_type': 'intervene_declining',
                'success': False,
                'error': str(e)
            }
