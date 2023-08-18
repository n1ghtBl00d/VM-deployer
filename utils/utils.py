

from functools import wraps
from flask import g, request, redirect, url_for

def user_data(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        raw_data = request.get_json()
       
        return f(raw_data.get('username', None), raw_data.get('password', None), *args, **kwargs)
    return decorated_function