from flask import Blueprint, session, request
from ..extensions import db
from ..database import User, Flag, Check_Flag, Dungeon
from ..utils import login_required

flag = Blueprint('flag', __name__)

@flag.post('')
@login_required
def submit_flag():
    if 'username' not in session:
        return {'Error': 'Not logged in'}, 401

    boss    = request.get_json().get('boss', None)
    level   = request.get_json().get('level', None)
    flag    = request.get_json().get('flag', None)

    if not boss and not level and not flag:
        return {'Error': 'Invalid value sent'}, 404
    
    if not level.isalnum() and not boss.isalnum():
        return {'Error': 'Invalid level or boss'}, 404
    print(level, boss, flag)
    if not Check_Flag.query.filter_by(level=level, boss=boss, flag=flag).first():
        return {'Error': 'Not a valid flag'}, 404

    # Get user from session
    username = session['username']
    user = User.query.filter_by(username=username).first()

    if not user:
        return {'Error': 'No user found'}

    flag = Flag(level=level, user_id=user.id, boss=boss)
    boss_info = Dungeon.query.filter_by(user_id=user.id, boss=boss).first()
    boss_info.is_dead = True
    db.session.add(flag)
    db.session.commit()
    return {'Success': 'Flag Submitted'}

@flag.get('')
@login_required
def get_submit():
    level = request.args.get('level', None)

    if not level:
        return {'Error': 'Invalid level or boss'}
    
    if 'username' not in session:
        return {'Error': 'Not valid user'}
    username = session['username']
    user = User.query.filter_by(username=username).first()

    if not user:
        return {'Error': 'No user found'}
    
    completed = Flag.query.filter_by(level=level, user_id=user.id).all()

    # bosses = Bosses.query.filter_by(level=level).first()
    