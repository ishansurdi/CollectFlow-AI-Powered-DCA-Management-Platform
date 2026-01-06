from config import Config
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def calculate_sla_deadline(priority):
    """
    Calculate SLA deadline based on priority
    """
    now = datetime.utcnow()
    
    sla_hours = {
        'critical': Config.SLA_CRITICAL,
        'high': Config.SLA_HIGH,
        'medium': Config.SLA_MEDIUM,
        'low': Config.SLA_LOW
    }
    
    hours = sla_hours.get(priority, Config.SLA_MEDIUM)
    deadline = now + timedelta(hours=hours)
    
    return deadline

def determine_priority(account):
    """
    Determine case priority based on account data
    """
    amount = account['amount_overdue']
    days = account['overdue_days']
    
    # Priority logic
    if amount >= 50000 or days >= 90:
        return 'critical'
    elif amount >= 25000 or days >= 60:
        return 'high'
    elif amount >= 10000 or days >= 30:
        return 'medium'
    else:
        return 'low'

def check_sla_breach(case):
    """
    Check if a case has breached SLA
    """
    if case['status'] in ['resolved', 'written_off']:
        return False
    
    if case.get('sla_deadline'):
        return datetime.utcnow() > case['sla_deadline']
    
    return False

def calculate_recovery_timeline(amount, priority, recovery_probability):
    """
    Calculate expected recovery timeline
    """
    base_days = {
        'critical': 15,
        'high': 30,
        'medium': 45,
        'low': 60
    }
    
    days = base_days.get(priority, 45)
    
    # Adjust based on recovery probability
    if recovery_probability < 0.3:
        days *= 1.5
    elif recovery_probability > 0.7:
        days *= 0.7
    
    return int(days)

def validate_case_assignment(case, dca):
    """
    Validate if a case can be assigned to a DCA
    """
    errors = []
    
    if dca['status'] != 'active':
        errors.append('DCA is not active')
    
    if dca['current_cases'] >= dca['capacity']:
        errors.append('DCA is at full capacity')
    
    if case['status'] not in ['pending', 'escalated']:
        errors.append('Case is not in assignable status')
    
    return len(errors) == 0, errors

def apply_business_rules(case, action):
    """
    Apply business rules before case actions
    """
    rules_passed = True
    messages = []
    
    # Rule: Can't resolve case without payment action
    if action == 'resolve':
        if not case.get('actions'):
            rules_passed = False
            messages.append('Cannot resolve case without documented actions')
    
    # Rule: Escalate if amount > $100k and overdue > 90 days
    if case.get('amount', 0) > 100000:
        from db.models import get_accounts_collection
        accounts = get_accounts_collection()
        account = accounts.find_one({'account_number': case['account_number']})
        if account and account['overdue_days'] > 90:
            messages.append('High-value case over 90 days - consider escalation')
    
    # Rule: Auto-escalate critical cases breaching SLA
    if case['priority'] == 'critical' and check_sla_breach(case):
        messages.append('Critical case has breached SLA - automatic escalation triggered')
    
    return rules_passed, messages
