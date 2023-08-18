from flask import Blueprint

flag = Blueprint('flag', __name__)

@flag.post('/')
def submit_flag():
    pass

@flag.delete('/')
def logout():
    pass
