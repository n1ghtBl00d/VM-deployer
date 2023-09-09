import os
basedir = os.path.abspath(os.path.dirname(__file__))

class default:
    SECRET_KEY = 'this_is_my_super_secret_key_right_now'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'app.db')}"
    SESSION_COOKIE_DOMAIN = 'thekeep.community'