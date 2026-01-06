import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config
import logging

logger = logging.getLogger(__name__)

def hash_password(password):
    """
    Hash a password using bcrypt
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """
    Verify a password against its hash
    """
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_token(user):
    """
    Generate JWT token for authenticated user
    """
    try:
        payload = {
            'user_id': user['user_id'],
            'email': user['email'],
            'role': user['role'],
            'dca_id': user.get('dca_id'),
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            Config.JWT_SECRET_KEY,
            algorithm='HS256'
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise

def decode_token(token):
    """
    Decode and verify JWT token
    """
    try:
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=['HS256']
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        raise ValueError('Token has expired')
    except jwt.InvalidTokenError:
        raise ValueError('Invalid token')

def token_required(f):
    """
    Decorator to require valid JWT token for route access
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Allow OPTIONS requests (CORS preflight) to pass through
        if request.method == 'OPTIONS':
            return f(None, *args, **kwargs)
        
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode token
            current_user = decode_token(token)
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            return jsonify({'error': 'Token verification failed'}), 401
        
        # Pass current_user to the route
        return f(current_user, *args, **kwargs)
    
    return decorated

def role_required(allowed_roles):
    """
    Decorator to require specific roles for route access
    """
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(current_user, *args, **kwargs):
            if current_user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(current_user, *args, **kwargs)
        
        return decorated
    return decorator

def validate_user_access(user, resource_type, resource_id):
    """
    Validate if user has access to a specific resource
    """
    # FedEx admins have access to everything
    if user['role'] == 'fedex_admin':
        return True
    
    # DCA users can only access their own resources
    if user['role'].startswith('dca'):
        if resource_type == 'case':
            from db.models import get_cases_collection
            cases = get_cases_collection()
            case = cases.find_one({'case_id': resource_id})
            if case:
                return case.get('assigned_dca') == user.get('dca_id')
        elif resource_type == 'dca':
            return resource_id == user.get('dca_id')
    
    # FedEx users have general access
    if user['role'].startswith('fedex'):
        return True
    
    return False
