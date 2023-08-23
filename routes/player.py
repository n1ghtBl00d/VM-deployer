from flask import Blueprint, request, session
from ..database import User, Flag, Dungeon
from ..extensions import db
from ..utils import user_data, login_required

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


@player.put('/player/key/<string:bossName>')
@login_required
def submit_key(bossName):
    user = User.query.filter_by(username=session['username']).first()

    boss_info = Dungeon.query.filter_by(user_id=user.id, boss=bossName).first()

    if not boss_info:
        return {'Error': 'Invalid boss'}, 404

    boss_info.key = True
    db.session.commit()
    return {'Success': 'Key added'}, 200


@player.get('/player/key/<string:level>')
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

    if key_count < 2:
        return {'error': 'Not enough keys', 'keys': int(key_count)}, 400
    
    return {'Success': 'YOU MAY PASS'}, 200