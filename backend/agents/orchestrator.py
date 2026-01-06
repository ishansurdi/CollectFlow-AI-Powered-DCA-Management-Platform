"""
Agent Orchestrator - Coordinates all autonomous agents
"""

from .case_agent import CaseManagementAgent
from .sla_agent import SLAMonitoringAgent
from .learning_agent import LearningAgent
from .recovery_agent import RecoveryOptimizationAgent
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging
import threading

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates multiple autonomous agents to work together.
    Manages agent lifecycle, scheduling, and coordination.
    """
    
    def __init__(self):
        self.agents = {}
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.lock = threading.Lock()
        
        # Initialize all agents
        self._initialize_agents()
        
        logger.info("Agent Orchestrator initialized")
    
    def _initialize_agents(self):
        """Initialize all autonomous agents"""
        self.agents = {
            'case_management': CaseManagementAgent(),
            'sla_monitoring': SLAMonitoringAgent(),
            'learning': LearningAgent(),
            'recovery_optimization': RecoveryOptimizationAgent()
        }
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    def start(self):
        """Start the orchestrator and all agents"""
        if self.is_running:
            logger.warning("Orchestrator already running")
            return
        
        try:
            # Schedule agent runs at different intervals
            
            # Case Management Agent - runs every 10 minutes
            self.scheduler.add_job(
                self._run_agent,
                'interval',
                minutes=10,
                args=['case_management'],
                id='case_management_job',
                max_instances=1
            )
            
            # SLA Monitoring Agent - runs every 5 minutes (critical)
            self.scheduler.add_job(
                self._run_agent,
                'interval',
                minutes=5,
                args=['sla_monitoring'],
                id='sla_monitoring_job',
                max_instances=1
            )
            
            # Recovery Optimization Agent - runs every 30 minutes
            self.scheduler.add_job(
                self._run_agent,
                'interval',
                minutes=30,
                args=['recovery_optimization'],
                id='recovery_optimization_job',
                max_instances=1
            )
            
            # Learning Agent - runs every 2 hours
            self.scheduler.add_job(
                self._run_agent,
                'interval',
                hours=2,
                args=['learning'],
                id='learning_job',
                max_instances=1
            )
            
            # Orchestration cycle - coordinates agents every 15 minutes
            self.scheduler.add_job(
                self._orchestration_cycle,
                'interval',
                minutes=15,
                id='orchestration_cycle',
                max_instances=1
            )
            
            # Health check - every hour
            self.scheduler.add_job(
                self._health_check,
                'interval',
                hours=1,
                id='health_check',
                max_instances=1
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Agent Orchestrator started - all agents active")
            
            # Run initial orchestration cycle
            self._orchestration_cycle()
            
        except Exception as e:
            logger.error(f"Error starting orchestrator: {str(e)}")
            raise
    
    def stop(self):
        """Stop the orchestrator and all agents"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Agent Orchestrator stopped")
            
        except Exception as e:
            logger.error(f"Error stopping orchestrator: {str(e)}")
    
    def _run_agent(self, agent_name):
        """Run a specific agent's cycle"""
        with self.lock:
            try:
                agent = self.agents.get(agent_name)
                if not agent:
                    logger.error(f"Agent {agent_name} not found")
                    return
                
                logger.info(f"Running agent: {agent_name}")
                
                # Get current environment state
                environment = self._get_environment_state()
                
                # Run agent cycle
                result = agent.run_cycle(environment)
                
                # Log result
                if result.get('action_taken'):
                    logger.info(
                        f"Agent {agent_name} completed cycle - "
                        f"Action taken: {result.get('result', {}).get('outcome', 'N/A')}"
                    )
                else:
                    logger.debug(f"Agent {agent_name} completed cycle - No action taken")
                
                return result
                
            except Exception as e:
                logger.error(f"Error running agent {agent_name}: {str(e)}")
                return {'error': str(e)}
    
    def _orchestration_cycle(self):
        """Coordinate agents and handle inter-agent communication"""
        try:
            logger.info("Running orchestration cycle")
            
            # Get environment state
            environment = self._get_environment_state()
            
            # Collect insights from all agents
            agent_states = {}
            for name, agent in self.agents.items():
                agent_states[name] = agent.get_state()
            
            # Determine if any agent needs priority execution
            priority_actions = self._identify_priority_actions(agent_states, environment)
            
            if priority_actions:
                logger.info(f"Executing {len(priority_actions)} priority actions")
                for action in priority_actions:
                    self._execute_priority_action(action)
            
            # Log orchestration metrics
            self._log_orchestration_metrics(agent_states)
            
        except Exception as e:
            logger.error(f"Error in orchestration cycle: {str(e)}")
    
    def _health_check(self):
        """Check health of all agents"""
        try:
            logger.info("Running agent health check")
            
            healthy_agents = 0
            unhealthy_agents = []
            
            for name, agent in self.agents.items():
                state = agent.get_state()
                
                # Check if agent is functioning
                if state.get('state') == 'error':
                    unhealthy_agents.append(name)
                    logger.warning(f"Agent {name} is in error state")
                else:
                    healthy_agents += 1
            
            logger.info(
                f"Health check complete: {healthy_agents}/{len(self.agents)} agents healthy"
            )
            
            if unhealthy_agents:
                logger.error(f"Unhealthy agents: {', '.join(unhealthy_agents)}")
                # In production, this would trigger alerts
            
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
    
    def _get_environment_state(self):
        """Get current state of the entire system"""
        try:
            from db.models import (
                get_cases_collection,
                get_accounts_collection,
                get_dcas_collection
            )
            
            cases_col = get_cases_collection()
            accounts_col = get_accounts_collection()
            dcas_col = get_dcas_collection()
            
            # Get summary statistics
            environment = {
                'timestamp': datetime.utcnow(),
                'total_cases': cases_col.count_documents({}),
                'pending_cases': cases_col.count_documents({'status': 'pending'}),
                'assigned_cases': cases_col.count_documents({'status': 'assigned'}),
                'escalated_cases': cases_col.count_documents({'status': 'escalated'}),
                'resolved_cases': cases_col.count_documents({'status': 'resolved'}),
                'total_accounts': accounts_col.count_documents({}),
                'new_accounts': accounts_col.count_documents({'status': 'new'}),
                'active_dcas': dcas_col.count_documents({'status': 'active'}),
                'sla_breaches': cases_col.count_documents({
                    'sla_deadline': {'$lt': datetime.utcnow()},
                    'status': {'$nin': ['resolved', 'written_off', 'escalated']}
                })
            }
            
            return environment
            
        except Exception as e:
            logger.error(f"Error getting environment state: {str(e)}")
            return {'error': str(e)}
    
    def _identify_priority_actions(self, agent_states, environment):
        """Identify actions that need immediate attention"""
        priority_actions = []
        
        # Priority 1: SLA breaches
        if environment.get('sla_breaches', 0) > 0:
            priority_actions.append({
                'agent': 'sla_monitoring',
                'reason': 'SLA breaches detected',
                'urgency': 'critical'
            })
        
        # Priority 2: Too many pending cases
        if environment.get('pending_cases', 0) > 10:
            priority_actions.append({
                'agent': 'case_management',
                'reason': 'High number of pending cases',
                'urgency': 'high'
            })
        
        # Priority 3: New accounts piling up
        if environment.get('new_accounts', 0) > 20:
            priority_actions.append({
                'agent': 'case_management',
                'reason': 'New accounts need case creation',
                'urgency': 'medium'
            })
        
        return priority_actions
    
    def _execute_priority_action(self, action):
        """Execute a priority action"""
        try:
            agent_name = action['agent']
            logger.info(
                f"Executing priority action for {agent_name}: {action['reason']}"
            )
            
            # Run the agent immediately
            self._run_agent(agent_name)
            
        except Exception as e:
            logger.error(f"Error executing priority action: {str(e)}")
    
    def _log_orchestration_metrics(self, agent_states):
        """Log metrics about agent orchestration"""
        try:
            total_actions = sum(
                state.get('actions_taken_count', 0)
                for state in agent_states.values()
            )
            
            total_decisions = sum(
                state.get('decisions_made_count', 0)
                for state in agent_states.values()
            )
            
            avg_success_rate = 0
            active_agents = 0
            
            for name, state in agent_states.items():
                metrics = state.get('performance_metrics', {})
                if metrics.get('actions_count', 0) > 0:
                    success_rate = (
                        metrics['success_count'] / metrics['actions_count']
                    )
                    avg_success_rate += success_rate
                    active_agents += 1
            
            if active_agents > 0:
                avg_success_rate /= active_agents
            
            logger.info(
                f"Orchestration metrics - "
                f"Total actions: {total_actions}, "
                f"Total decisions: {total_decisions}, "
                f"Avg success rate: {avg_success_rate:.2%}"
            )
            
        except Exception as e:
            logger.error(f"Error logging metrics: {str(e)}")
    
    def get_status(self):
        """Get status of orchestrator and all agents"""
        status = {
            'orchestrator_running': self.is_running,
            'timestamp': datetime.utcnow().isoformat(),
            'agents': {}
        }
        
        for name, agent in self.agents.items():
            status['agents'][name] = agent.get_state()
        
        return status
    
    def run_agent_now(self, agent_name):
        """Manually trigger an agent to run immediately"""
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        return self._run_agent(agent_name)
    
    def reset_agent(self, agent_name):
        """Reset a specific agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        self.agents[agent_name].reset()
        logger.info(f"Reset agent: {agent_name}")
