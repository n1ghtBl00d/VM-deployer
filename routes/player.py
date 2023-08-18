from flask import Blueprint, request, session
from ..database import User, Flag
from ..extensions import db
from ..utils import user_data

player = Blueprint('player', __name__)

@player.post('/login')
@user_data
def login(username, password):
    if not username or not password:
        return {'error': 'Missing user data'}, 400

    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        session['username'] = username
        player_info = { 
            'username': username,
            'new_user': False
        }
        return player_info, 200
    else:
        return { 'error': 'Invalid username or password.'}, 401

@player.delete('/logout')
def logout():
    del session['username']
    return {}, 204


@player.post('/register')
@user_data
def register(username, password):
    if not username or not password:
        return {'error': 'Missing user data'}, 400
    
    user = User(username=username)
    if User.query.filter_by(username=username).first():
        return {'error': 'Username already taken'}, 400

    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session['username'] = username

    player_info = { 
        'username': username,
        'new_user': True
    }
    return player_info, 200