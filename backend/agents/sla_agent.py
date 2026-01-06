"""
SLA Monitoring Agent - Proactive SLA enforcement and breach prevention
"""

from .base_agent import BaseAgent
from db.models import get_cases_collection, get_dcas_collection, create_event
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)


class SLAMonitoringAgent(BaseAgent):
    """
    Autonomous agent that proactively monitors and enforces SLAs:
    - Predicts potential breaches before they occur
    - Takes preventive actions
    - Auto-escalates breached cases
    - Adjusts priorities dynamically
    """
    
    def __init__(self):
        super().__init__(name="SLAMonitoringAgent")
        self.decision_threshold = 0.7
        self.breach_prediction_hours = 24  # Predict breaches 24h in advance
    
    def perceive(self, environment):
        """
        Perceive cases at risk of SLA breach
        """
        try:
            cases_col = get_cases_collection()
            
            now = datetime.utcnow()
            breach_window = now + timedelta(hours=self.breach_prediction_hours)
            
            # Find cases already breached
            breached_cases = list(cases_col.find({
                'sla_deadline': {'$lt': now},
                'status': {'$nin': ['resolved', 'written_off', 'escalated']}
            }))
            
            # Find cases at risk (will breach in next 24 hours)
            at_risk_cases = list(cases_col.find({
                'sla_deadline': {
                    '$gte': now,
                    '$lt': breach_window
                },
                'status': {'$nin': ['resolved', 'written_off', 'escalated']}
            }))
            
            # Find cases with no progress
            stalled_cases = list(cases_col.find({
                'status': 'assigned',
                'assigned_at': {'$lt': now - timedelta(days=5)},
                '$or': [
                    {'last_action_at': {'$exists': False}},
                    {'last_action_at': {'$lt': now - timedelta(days=3)}}
                ]
            }))
            
            perception = {
                'timestamp': now,
                'breached_count': len(breached_cases),
                'at_risk_count': len(at_risk_cases),
                'stalled_count': len(stalled_cases),
                'breached_cases': breached_cases,
                'at_risk_cases': at_risk_cases,
                'stalled_cases': stalled_cases
            }
            
            logger.info(
                f"SLAAgent perception: {len(breached_cases)} breached, "
                f"{len(at_risk_cases)} at risk, {len(stalled_cases)} stalled"
            )
            
            return perception
            
        except Exception as e:
            logger.error(f"Error in SLA agent perception: {str(e)}")
            return {'error': str(e)}
    
    def decide(self, perception):
        """
        Decide on actions to prevent or handle SLA breaches
        """
        try:
            actions = []
            
            # Decision 1: Immediate escalation for breached cases
            for case in perception.get('breached_cases', []):
                actions.append({
                    'type': 'escalate_breach',
                    'case': case,
                    'urgency': 'critical',
                    'confidence': 0.95
                })
            
            # Decision 2: Preventive actions for at-risk cases
            for case in perception.get('at_risk_cases', []):
                prevention = self._decide_prevention_action(case)
                if prevention:
                    actions.append(prevention)
            
            # Decision 3: Nudge/reminder for stalled cases
            for case in perception.get('stalled_cases', []):
                actions.append({
                    'type': 'send_reminder',
                    'case': case,
                    'urgency': 'medium',
                    'confidence': 0.8
                })
            
            # Sort by urgency and confidence
            urgency_scores = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
            actions.sort(
                key=lambda x: (urgency_scores.get(x.get('urgency', 'low'), 0), x.get('confidence', 0)),
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
                f"SLAAgent decided on {len(actions)} actions "
                f"with avg confidence {decision['confidence']:.2f}"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in SLA agent decision: {str(e)}")
            return {'actions': [], 'confidence': 0, 'error': str(e)}
    
    def act(self, decision):
        """
        Execute SLA enforcement actions
        """
        results = {
            'timestamp': datetime.utcnow(),
            'actions_executed': [],
            'success_count': 0,
            'failure_count': 0
        }
        
        try:
            for action in decision.get('actions', []):
                if action.get('confidence', 0) < self.decision_threshold:
                    continue
                
                try:
                    if action['type'] == 'escalate_breach':
                        result = self._escalate_breach_action(action)
                    elif action['type'] == 'increase_priority':
                        result = self._increase_priority_action(action)
                    elif action['type'] == 'send_reminder':
                        result = self._send_reminder_action(action)
                    elif action['type'] == 'reassign_case':
                        result = self._reassign_case_action(action)
                    else:
                        continue
                    
                    results['actions_executed'].append(result)
                    if result.get('success'):
                        results['success_count'] += 1
                    else:
                        results['failure_count'] += 1
                        
                except Exception as e:
                    logger.error(f"Error executing SLA action {action['type']}: {str(e)}")
                    results['failure_count'] += 1
            
            results['success'] = results['success_count'] > 0
            results['action'] = 'sla_monitoring_cycle'
            results['outcome'] = f"{results['success_count']} successes, {results['failure_count']} failures"
            
            logger.info(
                f"SLAAgent executed {len(results['actions_executed'])} actions - "
                f"{results['success_count']} successful"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in SLA agent action: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': 'sla_monitoring_cycle',
                'outcome': 'failed'
            }
    
    # Helper methods
    
    def _decide_prevention_action(self, case):
        """Decide preventive action for at-risk case"""
        hours_to_breach = (case['sla_deadline'] - datetime.utcnow()).total_seconds() / 3600
        
        if hours_to_breach < 12 and case['priority'] != 'critical':
            # Escalate priority if less than 12 hours to breach
            return {
                'type': 'increase_priority',
                'case': case,
                'new_priority': self._get_higher_priority(case['priority']),
                'urgency': 'high',
                'confidence': 0.85
            }
        elif hours_to_breach < 24:
            # Send reminder to DCA
            return {
                'type': 'send_reminder',
                'case': case,
                'urgency': 'medium',
                'confidence': 0.75
            }
        
        return None
    
    def _get_higher_priority(self, current_priority):
        """Get next higher priority level"""
        priority_levels = ['low', 'medium', 'high', 'critical']
        try:
            current_index = priority_levels.index(current_priority)
            return priority_levels[min(current_index + 1, len(priority_levels) - 1)]
        except ValueError:
            return 'medium'
    
    def _escalate_breach_action(self, action):
        """Escalate breached case"""
        try:
            cases_col = get_cases_collection()
            case = action['case']
            
            breach_duration = datetime.utcnow() - case['sla_deadline']
            breach_hours = breach_duration.total_seconds() / 3600
            
            cases_col.update_one(
                {'case_id': case['case_id']},
                {
                    '$set': {
                        'status': 'escalated',
                        'escalated_at': datetime.utcnow(),
                        'escalation_reason': f'SLA breach by {breach_hours:.1f} hours',
                        'breach_hours': breach_hours,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Create event
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'sla_breach_escalation',
                'description': f"SLA breach - auto-escalated by agent after {breach_hours:.1f} hours",
                'user_id': self.agent_id,
                'metadata': {
                    'breach_hours': breach_hours,
                    'autonomous': True,
                    'agent': self.name
                }
            })
            
            logger.warning(
                f"Agent escalated breached case {case['case_id']} "
                f"({breach_hours:.1f}h over SLA)"
            )
            
            return {
                'action_type': 'escalate_breach',
                'case_id': case['case_id'],
                'breach_hours': breach_hours,
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to escalate breach: {str(e)}")
            return {
                'action_type': 'escalate_breach',
                'success': False,
                'error': str(e)
            }
    
    def _increase_priority_action(self, action):
        """Increase case priority"""
        try:
            cases_col = get_cases_collection()
            case = action['case']
            new_priority = action['new_priority']
            
            cases_col.update_one(
                {'case_id': case['case_id']},
                {
                    '$set': {
                        'priority': new_priority,
                        'priority_increased_at': datetime.utcnow(),
                        'priority_increase_reason': 'SLA risk prevention',
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            
            # Create event
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'priority_increased',
                'description': f"Priority auto-increased from {case['priority']} to {new_priority} to prevent SLA breach",
                'user_id': self.agent_id,
                'metadata': {
                    'old_priority': case['priority'],
                    'new_priority': new_priority,
                    'autonomous': True
                }
            })
            
            logger.info(
                f"Agent increased priority for case {case['case_id']} "
                f"from {case['priority']} to {new_priority}"
            )
            
            return {
                'action_type': 'increase_priority',
                'case_id': case['case_id'],
                'old_priority': case['priority'],
                'new_priority': new_priority,
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to increase priority: {str(e)}")
            return {
                'action_type': 'increase_priority',
                'success': False,
                'error': str(e)
            }
    
    def _send_reminder_action(self, action):
        """Send reminder to DCA - creates notification event"""
        try:
            case = action['case']
            hours_to_deadline = (case['sla_deadline'] - datetime.utcnow()).total_seconds() / 3600
            
            # Create reminder event with detailed information
            event = create_event({
                'event_type': 'reminder_sent',
                'case_id': case.get('case_id'),
                'description': f'Auto-reminder sent to DCA about case approaching SLA deadline',
                'timestamp': datetime.utcnow(),
                'metadata': {
                    'agent_name': self.name,
                    'autonomous': True,
                    'action_type': 'send_reminder',
                    'dca_id': case.get('assigned_dca'),
                    'sla_deadline': case.get('sla_deadline').isoformat() if case.get('sla_deadline') else None,
                    'hours_remaining': round(hours_to_deadline, 1),
                    'priority': case.get('priority', 'medium'),
                    'amount_due': case.get('amount', 0),
                    'decision': f'Send urgent reminder - Only {round(hours_to_deadline, 1)} hours until SLA breach',
                    'proposed_changes': {
                        'action_required': 'Immediate contact with customer',
                        'reason': f'Case approaching SLA deadline in {round(hours_to_deadline, 1)} hours'
                    },
                    'reasoning': f'Proactive SLA monitoring detected case at risk of breach'
                }
            })
            
            return {
                'success': True,
                'action_type': 'send_reminder',
                'case_id': case.get('case_id'),
                'dca_id': case.get('assigned_dca'),
                'event_id': event
            }
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _old_send_reminder_action(self, action):
        """Send reminder to DCA"""
        try:
            case = action['case']
            
            # Create event (in real system, would also send email/notification)
            create_event({
                'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                'case_id': case['case_id'],
                'event_type': 'reminder_sent',
                'description': f"Auto-reminder sent to DCA about case approaching SLA deadline",
                'user_id': self.agent_id,
                'metadata': {
                    'dca_id': case.get('assigned_dca'),
                    'hours_to_deadline': (case['sla_deadline'] - datetime.utcnow()).total_seconds() / 3600,
                    'autonomous': True
                }
            })
            
            logger.info(f"Agent sent reminder for case {case['case_id']}")
            
            return {
                'action_type': 'send_reminder',
                'case_id': case['case_id'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to send reminder: {str(e)}")
            return {
                'action_type': 'send_reminder',
                'success': False,
                'error': str(e)
            }
    
    def _reassign_case_action(self, action):
        """Reassign case to different DCA"""
        try:
            # This would use the routing model to find a better DCA
            # For now, just log the intent
            case = action['case']
            
            logger.info(f"Agent recommending reassignment for case {case['case_id']}")
            
            return {
                'action_type': 'reassign_case',
                'case_id': case['case_id'],
                'success': True,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to reassign case: {str(e)}")
            return {
                'action_type': 'reassign_case',
                'success': False,
                'error': str(e)
            }
