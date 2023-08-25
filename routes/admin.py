from flask import Blueprint, session, request, render_template, redirect, url_for
from ..extensions import db
from ..database import User, Flag, Check_Flag, Dungeon, Boss_Info
from ..utils import login_required, admin_required


admin = Blueprint('admin', __name__)

levels = [
    'dungeonOne',
    'dungeonTwo',
    'dungeonThree',
    'dungeonFour',
    'dungeonFive',
]

@admin.get('')
@admin_required
def load_admin():

    all_flags = Check_Flag.query.all()
    all_users = User.query.all()

    return render_template('admin.html', all_flag_info=all_flags, users=all_users, levels=levels)


@admin.post('/flag')
@admin_required
def add_flag():
    flag = request.form.get("flag", None)
    boss = request.form.get("boss", None)
    level = request.form.get("level", None)

    if not flag or not boss or not level:
        return {'Error': 'Missing important information'}
    new_flag = Check_Flag(flag=flag, boss=boss, level=level)

    db.session.add(new_flag)
    db.session.commit()
    return redirect(url_for('admin.load_admin'))


@admin.get('/player/<string:username>')
@admin_required
def make_admin(username):
    if not username:
        return {'Error': 'Missing important information'}
    
    user = User.query.filter_by(username=username).first()
    user.role = 'admin'
    db.session.commit()
    return redirect(url_for('admin.load_admin'))

@admin.get('/delete/<string:boss>')
@admin_required
def delete_flag(boss):
    if not boss:
        return {'Error': 'Nothing to delete'}
    Check_Flag.query.filter_by(boss=boss).delete()
    db.session.commit()

    return redirect(url_for('admin.load_admin'))
