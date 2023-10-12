from flask import Blueprint, request, session
from ..database import User, Flag, Dungeon
from ..extensions import db
from ..utils import user_data, login_required
from flask_cors import cross_origin
from datetime import datetime
from ..config import PROXMOX_NODE
import random

player = Blueprint('player', __name__)

@player.post('/login')
@user_data
def login(username, password):
    if not username or not password:
        return {'error': 'Missing user data'}, 400

    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        session['username'] = user.username
        session['role'] = user.role
        player_info = { 
            'username': username,
            'newPlayer': False,
            'badgeId': user.badge_id
        }
        return player_info, 200
    else:
        return { 'error': 'Invalid username or password.'}, 401

@player.delete('/logout')
def logout():
    session.pop('username')
    session.pop('role')
    return {}, 204

@player.get('/verify')
def is_logged_in():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        player_info = { 
            'username': session['username'],
            'newPlayer': False,
            'badgeId': user.badge_id
        }
        return player_info, 200
    
    return {'error': 'Not logged in'}, 401

@player.post('/register')
@user_data
def register(username, password):
    if not username or not password:
        return {'error': 'Missing user data'}, 400
    
    if User.query.filter_by(username=username).first():
        return {'error': 'Username already taken'}, 400

    prox_node = random.randint(0, len(PROXMOX_NODE) - 1)

    user = User(username=username, role='user', status_info=datetime.now(), node=PROXMOX_NODE[prox_node])
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    session['username'] = user.username
    session['role'] = 'user'

    player_info = { 
        'username': user.username,
        'newPlayer': True,
        'badgeId': user.badge_id
    }
    return player_info, 200


@player.put('/key/<string:bossName>')
@login_required
def submit_key(bossName):
    user = User.query.filter_by(username=session['username']).first()

    boss_info = Dungeon.query.filter_by(user_id=user.id, boss=bossName).first()

    if not boss_info:
        return {'Error': 'Invalid boss'}, 404

    if not boss_info.is_dead:
        return {'Error': 'Boss much be defeated first'}, 404

    boss_info.key = True
    db.session.commit()
    return {'Success': 'Key added'}, 200

@player.put('/badge/<string:badge_id>')
@login_required
def submit_badge(badge_id):
    if not badge_id.isalnum():
        return {'Error': 'Invalid Badge ID'}, 400
    user = User.query.filter_by(username=session['username']).first()
    user.badge_id = badge_id
    player_info = { 
        'username': user.username,
        'newPlayer': False,
        'badgeId': badge_id
    }
    
    db.session.commit()
    return player_info, 200


@player.get('/key/<string:level>')
@login_required
def get_keys(level):
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return {'error': 'User does not exist'}, 400

    bosses = Dungeon.query.filter_by(user_id=user.id, level=level)

    key_count = 0
    for boss in bosses:
        if boss.key:
            key_count += 1
            
    # if key_count < 4 and level == 'dungeonOne':
    #     return {'error': 'Not enough keys', 'keys': int(key_count)}, 400
    
    # if key_count < 2:
    #     return {'error': 'Not enough keys', 'keys': int(key_count)}, 400
    
    return {'Success': 'YOU MAY PASS'}, 200