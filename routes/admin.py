from flask import Blueprint, session, request, render_template, redirect, url_for, escape
from ..extensions import db
from ..database import User, Flag, Check_Flag, Dungeon, Boss_Info
from ..utils import login_required, admin_required, get_headers, get_levels


admin = Blueprint('admin', __name__)

@admin.get('/', defaults={'path': ''})
@admin.get('/<path:path>')
# @admin_required
def load_admin(path):
    lower_path = escape(path.lower())
    headers = get_headers(lower_path)
    
    table_data = None
    if lower_path == 'users':
        table_data = User.query.add_columns(db.column('username'), db.column('role')).all()
    elif lower_path == 'dungeon':
        table_data = Boss_Info.query.all()
    elif lower_path == 'flag':
        table_data = Check_Flag.query.all()

    if not table_data:
        return render_template('test.html', path=lower_path, headers=headers)

    return render_template('test.html', headers=headers, table_data=table_data, path=lower_path, levels=get_levels())


@admin.delete('')
# @admin_required
def delete_record():
    currentRecord = request.get_json().get('id', None)
    database = request.get_json().get('database', None)

    if not currentRecord or not database:
        return {'Error': f'Invalid information'}, 400
    
    lower_path = escape(database.lower())

    if lower_path == 'users':
        User.query.filter_by(id=currentRecord).delete()
    elif lower_path == 'dungeon':
        Boss_Info.query.filter_by(id=currentRecord).delete()
    elif lower_path == 'flag':
        Check_Flag.query.filter_by(id=currentRecord).delete()

    db.session.commit()
    

    return {"Success": f"Deleted record {int(currentRecord)} from {lower_path}"}, 200

@admin.put('')
# @admin_required
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

        if not role or not username:
            return {'Error': 'Missing data'}, 400
        
        if role not in allowed_roles:
            return {'Error': f'{escape(role)}, not valid'}
        
        user = User.query.filter_by(id=currentRecord).first()
        user.username = username
        user.role = role

    elif lower_path == 'dungeon':
        headers.pop('graphic key')
        boss_info = Boss_Info.query.filter_by(id=currentRecord).first()
        for header in headers:
            value = raw_data.get(header.lower(), None)
            
            if not value:
                return {'Error': 'Values cannot be empty'}, 400
            
            setattr(boss_info, header.lower(), value )

        boss_info.bossGraphicKey = raw_data['graphic key']
       
    elif lower_path == 'flag':
        flag = Check_Flag.query.filter_by(id=currentRecord).first()
        
        for header in headers:
            value = raw_data.get(header.lower(), None)
            if not value:
                return {'Error': f'{header} Values cannot be empty'}, 400
            
            setattr(flag, header.lower(),  value)

    db.session.commit()
    

    return {"Success": f"Deleted record {int(currentRecord)} from {lower_path}"}, 200


@admin.post('')
# @admin_required
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

        password = raw_data.get('password', '')

        if len(password) == 0:
            return {'Error': 'Password cannot be empty'}, 400
        new_entry.set_password(password)
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
        return {'Error': f'Not able to add value {escape(e)}'}, 400
    
    return {'Success' : 'Record added'}, 200