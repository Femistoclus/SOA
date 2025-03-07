from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Authentication required', 'error': str(e)}), 401
    return decorated