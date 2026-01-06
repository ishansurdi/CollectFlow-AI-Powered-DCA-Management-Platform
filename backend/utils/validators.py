import re
from datetime import datetime

def validate_email(email):
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """
    Validate phone number format
    """
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Check if it's numeric and has valid length
    return cleaned.isdigit() and 10 <= len(cleaned) <= 15

def validate_amount(amount):
    """
    Validate monetary amount
    """
    try:
        value = float(amount)
        return value >= 0
    except (ValueError, TypeError):
        return False

def validate_date(date_string):
    """
    Validate date string format (ISO format)
    """
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False

def validate_priority(priority):
    """
    Validate case priority
    """
    valid_priorities = ['critical', 'high', 'medium', 'low']
    return priority in valid_priorities

def validate_status(status, entity_type='case'):
    """
    Validate status based on entity type
    """
    valid_statuses = {
        'case': ['pending', 'assigned', 'in_progress', 'resolved', 'escalated', 'written_off'],
        'account': ['new', 'assigned', 'in_progress', 'recovered', 'written_off'],
        'dca': ['active', 'inactive', 'suspended']
    }
    
    return status in valid_statuses.get(entity_type, [])

def validate_case_data(case_data):
    """
    Validate case creation data
    """
    errors = []
    
    if not case_data.get('account_number'):
        errors.append('account_number is required')
    
    if 'priority' in case_data and not validate_priority(case_data['priority']):
        errors.append('Invalid priority value')
    
    if 'amount' in case_data and not validate_amount(case_data['amount']):
        errors.append('Invalid amount value')
    
    return len(errors) == 0, errors

def validate_dca_data(dca_data):
    """
    Validate DCA data
    """
    errors = []
    
    if not dca_data.get('name'):
        errors.append('name is required')
    
    if not dca_data.get('email') or not validate_email(dca_data['email']):
        errors.append('Valid email is required')
    
    if 'capacity' in dca_data:
        try:
            capacity = int(dca_data['capacity'])
            if capacity < 0:
                errors.append('capacity must be non-negative')
        except (ValueError, TypeError):
            errors.append('capacity must be a number')
    
    return len(errors) == 0, errors

def validate_user_data(user_data):
    """
    Validate user registration data
    """
    errors = []
    
    if not user_data.get('email') or not validate_email(user_data['email']):
        errors.append('Valid email is required')
    
    if not user_data.get('password'):
        errors.append('password is required')
    elif len(user_data['password']) < 8:
        errors.append('password must be at least 8 characters')
    
    if not user_data.get('name'):
        errors.append('name is required')
    
    valid_roles = ['fedex_admin', 'fedex_user', 'dca_admin', 'dca_agent']
    if not user_data.get('role') or user_data['role'] not in valid_roles:
        errors.append(f'role must be one of: {", ".join(valid_roles)}')
    
    return len(errors) == 0, errors

def validate_account_number(account_number):
    """
    Validate account number format
    """
    if not account_number:
        return False
    # Assuming account numbers are alphanumeric with 6-20 characters
    return bool(re.match(r'^[A-Z0-9]{6,20}$', str(account_number).upper()))

def sanitize_input(input_string, max_length=None):
    """
    Sanitize user input to prevent injection attacks
    """
    if not isinstance(input_string, str):
        return str(input_string)
    
    # Remove potentially dangerous characters
    sanitized = input_string.strip()
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized

def validate_pagination_params(page, per_page, max_per_page=100):
    """
    Validate pagination parameters
    """
    errors = []
    
    try:
        page = int(page)
        if page < 1:
            errors.append('page must be >= 1')
    except (ValueError, TypeError):
        errors.append('page must be a number')
        page = 1
    
    try:
        per_page = int(per_page)
        if per_page < 1:
            errors.append('per_page must be >= 1')
        elif per_page > max_per_page:
            errors.append(f'per_page must be <= {max_per_page}')
            per_page = max_per_page
    except (ValueError, TypeError):
        errors.append('per_page must be a number')
        per_page = 10
    
    return (len(errors) == 0, errors, page, per_page)
