"""
Base Agent Class - Foundation for all autonomous agents
"""

from abc import ABC, abstractmethod
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all autonomous agents in the system
    """
    
    def __init__(self, agent_id=None, name=None):
        self.agent_id = agent_id or f"AGENT-{uuid.uuid4().hex[:8].upper()}"
        self.name = name or self.__class__.__name__
        self.state = "initialized"
        self.actions_taken = []
        self.decisions_made = []
        self.learning_data = []
        self.last_action_time = None
        self.performance_metrics = {
            'actions_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'avg_confidence': 0.0
        }
        
        logger.info(f"Agent {self.name} ({self.agent_id}) initialized")
    
    @abstractmethod
    def perceive(self, environment):
        """
        Perceive the current state of the environment
        
        Args:
            environment: Current environment state (cases, DCAs, etc.)
            
        Returns:
            dict: Perceived state relevant to this agent
        """
        pass
    
    @abstractmethod
    def decide(self, perception):
        """
        Make decisions based on perception
        
        Args:
            perception: Output from perceive()
            
        Returns:
            dict: Decision with action plan
        """
        pass
    
    @abstractmethod
    def act(self, decision):
        """
        Execute the decided action
        
        Args:
            decision: Output from decide()
            
        Returns:
            dict: Result of the action
        """
        pass
    
    def learn(self, action_result):
        """
        Learn from the outcome of actions
        
        Args:
            action_result: Result from act()
        """
        # Store learning data
        self.learning_data.append({
            'timestamp': datetime.utcnow(),
            'action': action_result.get('action'),
            'outcome': action_result.get('outcome'),
            'success': action_result.get('success', False)
        })
        
        # Update performance metrics
        self.performance_metrics['actions_count'] += 1
        if action_result.get('success'):
            self.performance_metrics['success_count'] += 1
        else:
            self.performance_metrics['failure_count'] += 1
        
        # Calculate success rate
        success_rate = (
            self.performance_metrics['success_count'] / 
            self.performance_metrics['actions_count']
        ) if self.performance_metrics['actions_count'] > 0 else 0
        
        logger.info(
            f"Agent {self.name} learning - Success rate: {success_rate:.2%}"
        )
    
    def run_cycle(self, environment):
        """
        Execute one complete perception-decision-action-learning cycle
        
        Args:
            environment: Current environment state
            
        Returns:
            dict: Cycle results
        """
        try:
            self.state = "active"
            
            # Perceive
            perception = self.perceive(environment)
            
            # Decide
            decision = self.decide(perception)
            
            # Record decision
            self.decisions_made.append({
                'timestamp': datetime.utcnow(),
                'decision': decision,
                'confidence': decision.get('confidence', 0.0)
            })
            
            # Act only if decision confidence is above threshold
            if decision.get('confidence', 0) > decision.get('threshold', 0.5):
                action_result = self.act(decision)
                
                # Record action
                self.actions_taken.append({
                    'timestamp': datetime.utcnow(),
                    'action': action_result
                })
                self.last_action_time = datetime.utcnow()
                
                # Learn
                self.learn(action_result)
                
                return {
                    'agent': self.name,
                    'cycle_complete': True,
                    'action_taken': True,
                    'result': action_result
                }
            else:
                logger.info(
                    f"Agent {self.name} decided not to act - "
                    f"confidence {decision.get('confidence', 0)} below threshold"
                )
                return {
                    'agent': self.name,
                    'cycle_complete': True,
                    'action_taken': False,
                    'reason': 'low_confidence'
                }
                
        except Exception as e:
            logger.error(f"Error in agent {self.name} cycle: {str(e)}")
            self.state = "error"
            return {
                'agent': self.name,
                'cycle_complete': False,
                'error': str(e)
            }
        finally:
            self.state = "idle"
    
    def get_state(self):
        """Get current agent state"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'state': self.state,
            'actions_taken_count': len(self.actions_taken),
            'decisions_made_count': len(self.decisions_made),
            'performance_metrics': self.performance_metrics,
            'last_action_time': self.last_action_time.isoformat() if self.last_action_time else None
        }
    
    def reset(self):
        """Reset agent state"""
        self.state = "initialized"
        self.actions_taken = []
        self.decisions_made = []
        logger.info(f"Agent {self.name} reset")
