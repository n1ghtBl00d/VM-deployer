

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


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return {'Error': 'Not logged in'}, 401
        
        role = session.get('role', 'user')

        if role.lower() != 'admin':
            return {'Error': 'You are not ADMIN!'}
        
        return f(*args, **kwargs)
    return decorated_function

def get_headers(header):
    headers = {
        "users": [
            'Username',
            'Score',
            'Role'
        ],
        "dungeon": [
            "Level",
            "Boss",
            "Description",
            "VMID",
            "Strengths",
            "Weaknesses",
            "Graphic key"
        ],
        "flag": [
            "Level",
            "Boss",
            "Flag"
        ]
    }
    
    return headers.get(header.lower(), {})

def get_levels():
    return [
        'dungeonOne',
        'dungeonTwo',
        'dungeonThree',
        'dungeonFour',
        'dungeonFive',
    ]