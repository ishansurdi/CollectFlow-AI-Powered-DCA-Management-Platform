from db.models import get_cases_collection, get_dcas_collection, create_event
from services.workflow_service import check_sla_breach
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import uuid

logger = logging.getLogger(__name__)

class SLAEngine:
    """
    SLA monitoring and enforcement engine
    Runs periodic checks and triggers escalations
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """
        Start the SLA monitoring engine
        """
        if not self.is_running:
            # Schedule SLA check every 15 minutes
            self.scheduler.add_job(
                self.check_sla_breaches,
                'interval',
                minutes=15,
                id='sla_check'
            )
            
            # Schedule daily performance update
            self.scheduler.add_job(
                self.update_dca_performance,
                'interval',
                hours=24,
                id='performance_update'
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("SLA Engine started")
    
    def stop(self):
        """
        Stop the SLA monitoring engine
        """
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("SLA Engine stopped")
    
    def check_sla_breaches(self):
        """
        Check for SLA breaches and trigger escalations
        """
        try:
            logger.info("Running SLA breach check...")
            
            cases = get_cases_collection()
            
            # Find cases that have breached SLA
            breached_cases = cases.find({
                'sla_deadline': {'$lt': datetime.utcnow()},
                'status': {'$nin': ['resolved', 'written_off', 'escalated']}
            })
            
            breach_count = 0
            for case in breached_cases:
                self._handle_sla_breach(case)
                breach_count += 1
            
            if breach_count > 0:
                logger.warning(f"Found {breach_count} SLA breaches")
            else:
                logger.info("No SLA breaches found")
            
            return breach_count
            
        except Exception as e:
            logger.error(f"Error checking SLA breaches: {str(e)}")
            return 0
    
    def _handle_sla_breach(self, case):
        """
        Handle a specific SLA breach
        """
        try:
            cases = get_cases_collection()
            
            # Calculate breach duration
            breach_hours = (datetime.utcnow() - case['sla_deadline']).total_seconds() / 3600
            
            # Update case status based on priority
            if case['priority'] == 'critical':
                # Immediate escalation for critical cases
                cases.update_one(
                    {'case_id': case['case_id']},
                    {
                        '$set': {
                            'status': 'escalated',
                            'escalation_reason': f'SLA breach: {breach_hours:.1f} hours overdue',
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                # Log escalation event
                create_event({
                    'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                    'case_id': case['case_id'],
                    'event_type': 'sla_breach_escalation',
                    'description': f"Critical case escalated due to SLA breach ({breach_hours:.1f}h overdue)",
                    'user_id': 'system',
                    'metadata': {
                        'breach_hours': breach_hours,
                        'priority': case['priority']
                    }
                })
                
                logger.warning(f"Case {case['case_id']} escalated due to SLA breach")
                
            else:
                # Just flag the breach for other priorities
                cases.update_one(
                    {'case_id': case['case_id']},
                    {
                        '$set': {
                            'sla_breached': True,
                            'breach_hours': breach_hours,
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                
                # Log breach event
                create_event({
                    'event_id': f"EVT-{uuid.uuid4().hex[:8].upper()}",
                    'case_id': case['case_id'],
                    'event_type': 'sla_breach',
                    'description': f"SLA breach detected ({breach_hours:.1f}h overdue)",
                    'user_id': 'system',
                    'metadata': {
                        'breach_hours': breach_hours,
                        'priority': case['priority']
                    }
                })
                
                logger.info(f"Case {case['case_id']} flagged for SLA breach")
            
        except Exception as e:
            logger.error(f"Error handling SLA breach for case {case.get('case_id')}: {str(e)}")
    
    def check_case_sla(self, case_id):
        """
        Check SLA status for a specific case
        """
        try:
            cases = get_cases_collection()
            case = cases.find_one({'case_id': case_id})
            
            if not case:
                raise ValueError(f"Case {case_id} not found")
            
            if case['status'] in ['resolved', 'written_off']:
                return {
                    'case_id': case_id,
                    'status': 'completed',
                    'sla_met': True
                }
            
            sla_deadline = case.get('sla_deadline')
            if not sla_deadline:
                return {
                    'case_id': case_id,
                    'status': 'no_sla',
                    'sla_met': None
                }
            
            now = datetime.utcnow()
            is_breached = now > sla_deadline
            
            if is_breached:
                hours_breached = (now - sla_deadline).total_seconds() / 3600
                return {
                    'case_id': case_id,
                    'status': 'breached',
                    'sla_met': False,
                    'breach_hours': round(hours_breached, 2),
                    'deadline': sla_deadline.isoformat()
                }
            else:
                hours_remaining = (sla_deadline - now).total_seconds() / 3600
                return {
                    'case_id': case_id,
                    'status': 'active',
                    'sla_met': True,
                    'hours_remaining': round(hours_remaining, 2),
                    'deadline': sla_deadline.isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error checking case SLA: {str(e)}")
            raise
    
    def update_dca_performance(self):
        """
        Update performance scores for all DCAs
        """
        try:
            logger.info("Updating DCA performance scores...")
            
            from services.dca_service import update_dca_performance_score
            
            dcas = get_dcas_collection()
            active_dcas = dcas.find({'status': 'active'})
            
            count = 0
            for dca in active_dcas:
                try:
                    update_dca_performance_score(dca['dca_id'])
                    count += 1
                except Exception as e:
                    logger.error(f"Error updating performance for DCA {dca['dca_id']}: {str(e)}")
            
            logger.info(f"Updated performance scores for {count} DCAs")
            return count
            
        except Exception as e:
            logger.error(f"Error updating DCA performance: {str(e)}")
            return 0
    
    def get_sla_report(self):
        """
        Generate SLA compliance report
        """
        try:
            cases = get_cases_collection()
            
            # Total active cases
            total_active = cases.count_documents({
                'status': {'$nin': ['resolved', 'written_off']}
            })
            
            # Cases breaching SLA
            breached = cases.count_documents({
                'sla_deadline': {'$lt': datetime.utcnow()},
                'status': {'$nin': ['resolved', 'written_off']}
            })
            
            # Cases resolved within SLA
            resolved_on_time = cases.count_documents({
                'status': 'resolved',
                'resolved_at': {'$lte': '$sla_deadline'}
            })
            
            # Total resolved cases
            total_resolved = cases.count_documents({'status': 'resolved'})
            
            # Calculate compliance rate
            compliance_rate = ((total_resolved - breached) / total_resolved * 100) if total_resolved > 0 else 100
            
            # Breaches by priority
            breaches_by_priority = {}
            for priority in ['critical', 'high', 'medium', 'low']:
                count = cases.count_documents({
                    'priority': priority,
                    'sla_deadline': {'$lt': datetime.utcnow()},
                    'status': {'$nin': ['resolved', 'written_off']}
                })
                breaches_by_priority[priority] = count
            
            report = {
                'total_active_cases': total_active,
                'active_breaches': breached,
                'compliance_rate': round(compliance_rate, 2),
                'resolved_on_time': resolved_on_time,
                'total_resolved': total_resolved,
                'breaches_by_priority': breaches_by_priority,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating SLA report: {str(e)}")
            raise

# Global SLA engine instance
sla_engine = SLAEngine()

def start_sla_engine():
    """
    Start the global SLA engine
    """
    sla_engine.start()

def stop_sla_engine():
    """
    Stop the global SLA engine
    """
    sla_engine.stop()

def get_sla_engine():
    """
    Get the global SLA engine instance
    """
    return sla_engine
