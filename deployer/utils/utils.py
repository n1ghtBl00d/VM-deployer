

from functools import wraps
from flask import g, request, session, redirect

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
            return redirect("/admin/login")
        
        role = session.get('role', 'user')

        if role.lower() != 'admin':
            return redirect("/admin/login")
        
        return f(*args, **kwargs)
    return decorated_function

def get_headers(header):
    headers = {
        "users": [
            'Username',
            'Password',
            'Role'
        ],
        "dungeon": [
            "Level",
            "Boss",
            "Bossname",
            "Description",
            "VMID",
            "Strengths",
            "Weaknesses",
            "Boss_graphic_key"
        ],
        "flag": [
            "Level",
            "Boss",
            "Flag"
        ],
        "machines": [
            "Username",
            "Machine_id",
            "Template_id",
            "IP",
            "Machine_name"
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