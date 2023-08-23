

from functools import wraps
from flask import g, request, session

def user_data(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        raw_data = request.get_json()
       
        return f(raw_data.get('username', None), raw_data.get('password', None), *args, **kwargs)
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return {'Error': 'Not logged in'}, 401
        return f(*args, **kwargs)
    return decorated_function
