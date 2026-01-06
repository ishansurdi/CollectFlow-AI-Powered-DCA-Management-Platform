from flask import Blueprint, request, jsonify
from utils.auth import generate_token, hash_password, verify_password, token_required
from db.models import get_users_collection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint for both FedEx and DCA users
    Expected payload: {email, password}
    """
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        users = get_users_collection()
        user = users.find_one({'email': email})
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.get('is_active', False):
            return jsonify({'error': 'Account is inactive'}), 403
        
        if not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Update last login
        users.update_one(
            {'email': email},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        # Generate token
        token = generate_token(user)
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            'token': token,
            'user': {
                'user_id': user['user_id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'dca_id': user.get('dca_id')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/register', methods=['POST'])
@token_required
def register(current_user):
    """
    Register new user (admin only)
    Expected payload: {email, password, name, role, dca_id (optional)}
    """
    try:
        # Only admins can create users
        if current_user['role'] not in ['fedex_admin', 'dca_admin']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role')
        dca_id = data.get('dca_id')
        
        if not all([email, password, name, role]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        users = get_users_collection()
        
        # Check if user already exists
        if users.find_one({'email': email}):
            return jsonify({'error': 'User already exists'}), 400
        
        # Create user
        user_id = f"user_{datetime.utcnow().timestamp()}"
        user_data = {
            'user_id': user_id,
            'email': email,
            'password_hash': hash_password(password),
            'name': name,
            'role': role,
            'created_at': datetime.utcnow(),
            'is_active': True
        }
        
        if dca_id:
            user_data['dca_id'] = dca_id
        
        users.insert_one(user_data)
        
        logger.info(f"New user created: {email}")
        
        return jsonify({
            'message': 'User created successfully',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """Verify if token is valid"""
    return jsonify({
        'valid': True,
        'user': {
            'user_id': current_user['user_id'],
            'email': current_user['email'],
            'role': current_user['role']
        }
    }), 200

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change user password"""
    try:
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not all([old_password, new_password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        users = get_users_collection()
        user = users.find_one({'user_id': current_user['user_id']})
        
        if not verify_password(old_password, user['password_hash']):
            return jsonify({'error': 'Invalid current password'}), 401
        
        # Update password
        users.update_one(
            {'user_id': current_user['user_id']},
            {'$set': {'password_hash': hash_password(new_password)}}
        )
        
        logger.info(f"Password changed for user: {current_user['email']}")
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return jsonify({'error': 'Password change failed'}), 500
