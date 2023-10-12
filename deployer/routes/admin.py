from flask import Blueprint, session, request, render_template, redirect, url_for, escape
from ..extensions import db
from ..database import User, Flag, Check_Flag, Dungeon, Boss_Info, Machines
from ..utils import login_required, admin_required, get_headers, get_levels
from ..config import *
import datetime

admin = Blueprint('admin', __name__)

@admin.get('/login')
def admin_login():
    return render_template('login.html')

@admin.post('/login')
def post_admin_login():
    error = "Invalid creds"
    user = request.form.get('username', None)
    password = request.form.get('password', None)

    if not user or not password:
        return render_template('login.html', error=error)
    user = User.query.filter_by(username=user).first()
    
    if user and user.check_password(password):
        if user.role != 'admin':
            return render_template('login.html', error=error)
        
        session['username'] = user.username
        session['role'] = user.role
        return redirect('/admin/dashboard')
    
    return render_template('login.html', error=error)

@admin.get('/', defaults={'path': ''})
@admin.get('/<path:path>')
@admin_required
def load_admin(path):
    lower_path = escape(path.lower())
    headers = get_headers(lower_path)
  
    # Get list of all Bosses and Levels
    boss_info = Boss_Info.query.distinct()
    bosses = [r.boss for r in boss_info]
    levels = set(r.level for r in boss_info)
    table_data = None
    if lower_path == 'users':
        table_data = User.query.add_columns(db.column('username'), db.column('role'), db.column('id')).all()
    elif lower_path == 'dungeon':
        table_data = Boss_Info.query.order_by(Boss_Info.level).all()
    elif lower_path == 'flag':
        table_data = Check_Flag.query.all()
    elif lower_path == 'machines':
        table_data = Machines.query.order_by(Machines.username).all()



    if not table_data:
        return render_template('base.html', path=lower_path, headers=headers, boss=bosses, levels=levels, CLONE_RANGE_LOWER=CLONE_RANGE_LOWER, CLONE_RANGE_UPPER=CLONE_RANGE_UPPER)

    return render_template('base.html', headers=headers, table_data=table_data, path=lower_path, boss=bosses, levels=list(levels), CLONE_RANGE_LOWER=CLONE_RANGE_LOWER, CLONE_RANGE_UPPER=CLONE_RANGE_UPPER)


@admin.delete('')
@admin_required
def delete_record():
    currentRecord = request.get_json().get('id', None)
    database = request.get_json().get('database', None)

    if not currentRecord or not database:
        return {'Error': f'Invalid information'}, 400
    
    lower_path = escape(database.lower())

    if lower_path == 'users':
        User.query.filter_by(id=currentRecord).delete()
        Dungeon.query.filter_by(user_id=currentRecord).delete()
        Flag.query.filter_by(user_id=currentRecord).delete()
    elif lower_path == 'dungeon':
        Boss_Info.query.filter_by(id=currentRecord).delete()
    elif lower_path == 'flag':
        Check_Flag.query.filter_by(id=currentRecord).delete()

    db.session.commit()
    
    return {"Success": f"Deleted record {int(currentRecord)} from {lower_path}"}, 200

@admin.put('')
@admin_required
def edit_record():
    currentRecord = request.get_json().get('id', None)
    database = request.get_json().get('database', None)
    if not currentRecord or not database:
        return {'Error': f'Invalid information'}, 400
    
    lower_path = escape(database.lower())

    raw_data = request.get_json()
    headers = get_headers(database)
    if lower_path == 'users':
        allowed_roles = ('user', 'admin')

        username = raw_data.get('username', None)
        role = raw_data.get('role', None)
        password = raw_data('password', None)

        if not role or not username:
            return {'Error': 'Missing data'}, 400
        
        if role not in allowed_roles:
            return {'Error': f'{escape(role)}, not valid'}

        user = User.query.filter_by(id=currentRecord).first()
        if password:
            user.set_password(password)

        user.username = username
        user.role = role

    elif lower_path == 'dungeon':
        print("RAW DATA: ", raw_data, flush=True)
        
        # headers.pop(headers.index('Boss_graphic_key'))
        boss_info = Boss_Info.query.filter_by(id=currentRecord).first()
        for header in headers:
            value = raw_data.get(header.lower(), None)
            print("HEADER DATA: ", header.lower(), flush=True)
            print("VALUE DATA: ", value, flush=True)
            if not value:
                return {'Error': 'Values cannot be empty'}, 400
            
            if 'boss' == header.lower():
                raw_data.pop('boss', None)
                continue
            setattr(boss_info, header.lower(), value )

        boss_info.bossGraphicKey = raw_data['boss_graphic_key']
       
    elif lower_path == 'flag':
        flag = Check_Flag.query.filter_by(id=currentRecord).first()
        
        for header in headers:
            value = raw_data.get(header.lower(), None)
            if not value:
                return {'Error': f'{header} Values cannot be empty'}, 400
            
            setattr(flag, header.lower(),  value)

    db.session.commit()
    

    return {"Success": f"Updated record {int(currentRecord)} from {lower_path}"}, 200


@admin.post('')
@admin_required
def add_data():
    database = request.get_json().get('database', None)

    if not database:
        return {'Error': f'Invalid information'}, 400
    
    lower_path = escape(database.lower())
    
    raw_data = request.get_json()
    headers = get_headers(database)
    new_data = {}
    for header in headers:
        value = raw_data.get(header, None)
        if value is not None:
            new_data[header.lower()] = value

    if lower_path == 'users':
        new_entry = User(username=new_data['username'], role=new_data['role'])
        if not new_data.get('password', None):
            return {'Error': 'Password cannot be empty'}, 400 
        password = new_data.get('password', '')

        if len(password) == 0:
            return {'Error': 'Password cannot be empty'}, 400
        new_entry.set_password(password)
        new_entry.status_info = datetime.datetime.now()
    elif lower_path == 'dungeon':
        new_data['bossGraphicKey'] = raw_data['Graphickey']
        new_entry = Boss_Info(**new_data)
    elif lower_path == 'flag':
        if len(new_data.get('flag', '')) == 0:
            return {'Error': 'Flag cannot be empty'}, 400 
        new_entry = Check_Flag(**new_data)

    try:
        db.session.add(new_entry)
        db.session.commit()
    except Exception as e:
        print(e)
        return {'Error': f'Not able to add value {escape(e)}'}, 400
    
    return {'Success' : 'Record added'}, 200