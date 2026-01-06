"""
Case Management Agent - Autonomous case lifecycle management
"""

from .base_agent import BaseAgent
from db.models import (
    get_cases_collection,
    get_accounts_collection,
    get_dcas_collection,
    create_event
)
from services.ai_service import predict_recovery, recommend_dca
from services.workflow_service import calculate_sla_deadline, determine_priority
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


class CaseManagementAgent(BaseAgent):
    """
    Autonomous agent that manages the complete case lifecycle:
    - Creates cases from overdue accounts
    - Assigns to optimal DCAs
    - Monitors progress
    - Escalates when needed
    - Closes resolved cases
    """
    
    def __init__(self):
        super().__init__(name="CaseManagementAgent")
        self.decision_threshold = 0.6  # Confidence threshold for autonomous actions
        self.auto_escalate_threshold = 0.8  # Higher confidence for escalations
    
    def perceive(self, environment):
        """
        Perceive cases that need attention
        """
        try:
            cases_col = get_cases_collection()
            accounts_col = get_accounts_collection()
            dcas_col = get_dcas_collection()
            
            # Find cases needing action
            pending_cases = list(cases_col.find({'status': 'pending'}).limit(50))
            assigned_cases = list(cases_col.find({'status': 'assigned'}).limit(100))
            
            # Find unassigned overdue accounts
            new_accounts = list(accounts_col.find({
                'status': 'new',
                'overdue_days': {'$gte': 7}
            }).limit(20))
            
            # Get DCA availability
            available_dcas = list(dcas_col.find({
                'status': 'active',
                '$expr': {'$lt': ['$current_cases', '$capacity']}
            }))
            
            perception = {
                'timestamp': datetime.utcnow(),
                'pending_cases_count': len(pending_cases),
                'assigned_cases_count': len(assigned_cases),
                'new_accounts_count': len(new_accounts),
                'available_dcas_count': len(available_dcas),
                'pending_cases': pending_cases,
                'assigned_cases': assigned_cases,
                'new_accounts': new_accounts,
                'available_dcas': available_dcas
            }
            
            logger.info(
                f"CaseAgent perception: {len(pending_cases)} pending, "
                f"{len(new_accounts)} new accounts, {len(available_dcas)} DCAs available"
            )
            
            return perception
            
        except Exception as e:
            logger.error(f"Error in case agent perception: {str(e)}")
            return {'error': str(e)}
    
    def decide(self, perception):
        """
        Decide what actions to take based on perception
        """
        try:
            actions = []
            
            # Decision 1: Create cases for new accounts
            for account in perception.get('new_accounts', []):
                if self._should_create_case(account):
                    actions.append({
                        'type': 'create_case',
                        'account': account,
                        'priority': determine_priority(account),
                        'confidence': self._calculate_case_creation_confidence(account)
                    })
            
            # Decision 2: Assign pending cases to DCAs
            for case in perception.get('pending_cases', []):
                if perception.get('available_dcas'):
                    dca_recommendation = self._recommend_dca_for_case(
                        case, 
                        perception['available_dcas']
                    )
                    if dca_recommendation:
                        actions.append({
                            'type': 'assign_case',
                            'case': case,
                            'dca': dca_recommendation['dca'],
                            'confidence': dca_recommendation['confidence']
                        })
            
            # Decision 3: Check assigned cases for escalation
            for case in perception.get('assigned_cases', []):
                escalation_decision = self._should_escalate_case(case)
                if escalation_decision['should_escalate']:
                    actions.append({
                        'type': 'escalate_case',
                        'case': case,
                        'reason': escalation_decision['reason'],
                        'confidence': escalation_decision['confidence']
                    })
            
            # Prioritize actions by confidence and priority
            actions.sort(
                key=lambda x: (x.get('confidence', 0), self._get_action_priority(x)),
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
                f"CaseAgent decided on {len(actions)} actions "
                f"with avg confidence {decision['confidence']:.2f}"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in case agent decision: {str(e)}")
            return {'actions': [], 'confidence': 0, 'error': str(e)}
    
    def act(self, decision):
        """
        Execute the decided actions
        """
        results = {
            'timestamp': datetime.utcnow(),
            'actions_executed': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        try:
            for action in decision.get('actions', []):
                # Only execute if confidence is above threshold
                if action.get('confidence', 0) < self.decision_threshold:
                    continue
                
                try:
                    if action['type'] == 'create_case':
                        result = self._create_case_action(action)
                    elif action['type'] == 'assign_case':
                        result = self._assign_case_action(action)
                    elif action['type'] == 'escalate_case':
                        result = self._escalate_case_action(action)
                    else:
                        continue
                    
                    results['actions_executed'].append(result)
                    if result.get('success'):
                        results['success_count'] += 1
                    else:
                        results['failure_count'] += 1
                        
                except Exception as e:
                    logger.error(f"Error executing action {action['type']}: {str(e)}")
                    results['failure_count'] += 1
            
            results['success'] = results['success_count'] > 0
            results['action'] = 'case_management_cycle'
            results['outcome'] = f"{results['success_count']} successes, {results['failure_count']} failures"
            
            logger.info(
                f"CaseAgent executed {len(results['actions_executed'])} actions - "
                f"{results['success_count']} successful"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in case agent action: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': 'case_management_cycle',
                'outcome': 'failed'
            }
    
    # Helper methods
    
    def _should_create_case(self, account):
        """Determine if a case should be created for an account"""
        return (
            account['overdue_days'] >= 7 and
            account['amount_overdue'] > 0 and
            account['status'] == 'new'
        )
    
    def _calculate_case_creation_confidence(self, account):
        """Calculate confidence for case creation"""
        confidence = 0.5
        
        # Higher confidence for older debts
        if account['overdue_days'] >= 30:
            confidence += 0.2
        elif account['overdue_days'] >= 14:
            confidence += 0.1
        
        # Higher confidence for larger amounts
        if account['amount_overdue'] >= 10000:
            confidence += 0.2
        elif account['amount_overdue'] >= 5000:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _recommend_dca_for_case(self, case, available_dcas):
        """Recommend best DCA for a case"""
        try:
            # Use AI routing model
            recommendation = recommend_dca(case['case_id'], None)
            
            # Find the recommended DCA in available list
            recommended_dca = next(
                (dca for dca in available_dcas if dca['dca_id'] == recommendation['recommended_dca']),
                None
            )
            
            if recommended_dca:
                return {
                    'dca': recommended_dca,
                    'confidence': min(recommendation['score'] / 100, 1.0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error recommending DCA: {str(e)}")
            # Fallback: pick DCA with lowest utilization
            if available_dcas:
                dca = min(available_dcas, key=lambda d: d['current_cases'] / d['capacity'])
                return {'dca': dca, 'confidence': 0.5}
            return None
    
    def _should_escalate_case(self, case):
        """Determine if a case should be escalated"""
        # Check SLA breach
        if case.get('sla_deadline') and datetime.utcnow() > case['sla_deadline']:
            return {
                'should_escalate': True,
                'reason': 'SLA breach',
                'confidence': 0.9
            }
        
        # Check if no progress for 7 days
        if case.get('assigned_at'):
            days_since_assignment = (datetime.utcnow() - case['assigned_at']).days
            if days_since_assignment >= 7 and case.get('last_action_at') is None:
                return {
                    'should_escalate': True,
                    'reason': 'No progress for 7 days',
                    'confidence': 0.8
                }
        
        return {
            'should_escalate': False,
            'reason': None,
            'confidence': 0
        }
    
    def _get_action_priority(self, action):
        """Get priority score for an action"""
        priorities = {
            'escalate_case': 3,
            'assign_case': 2,
            'create_case': 1
        }
        return priorities.get(action['type'], 0)
    
    def _create_case_action(self, action):
        """Execute case creation"""
        try:
            from services.case_service import create_new_case
            
            account = action['account']
            case_data = create_new_case(
                account['account_number'],
                priority=action['priority'],
                user_id=self.agent_id
            )
            
            logger.info(f"Agent created case {case_data['case_id']} for account {account['account_number']}")
            
            return {
                'action_type': 'create_case',
                'case_id': case_data['case_id'],
                'account_number': account['account_number'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to create case: {str(e)}")
            return {
                'action_type': 'create_case',
                'success': False,
                'error': str(e)
            }
    
    def _assign_case_action(self, action):
        """Execute case assignment"""
        try:
            from services.case_service import assign_case_to_dca
            
            case = action['case']
            dca = action['dca']
            
            assign_case_to_dca(case['case_id'], dca['dca_id'], self.agent_id)
            
            logger.info(f"Agent assigned case {case['case_id']} to DCA {dca['dca_id']}")
            
            return {
                'action_type': 'assign_case',
                'case_id': case['case_id'],
                'dca_id': dca['dca_id'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to assign case: {str(e)}")
            return {
                'action_type': 'assign_case',
                'success': False,
                'error': str(e)
            }
    
    def _escalate_case_action(self, action):
        """Execute case escalation"""
        try:
            cases = get_cases_collection()
            case = action['case']
            
            cases.update_one(
                {'case_id': case['case_id']},
                {
                    '$set': {
                        'status': 'escalated',
                        'escalated_at': datetime.utcnow(),
                        'escalation_reason': action['reason'],
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Create event
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'case_escalated',
                'description': f"Case auto-escalated by agent: {action['reason']}",
                'user_id': self.agent_id,
                'metadata': {'reason': action['reason'], 'autonomous': True}
            })
            
            logger.warning(f"Agent escalated case {case['case_id']}: {action['reason']}")
            
            return {
                'action_type': 'escalate_case',
                'case_id': case['case_id'],
                'reason': action['reason'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to escalate case: {str(e)}")
            return {
                'action_type': 'escalate_case',
                'success': False,
                'error': str(e)
            }
