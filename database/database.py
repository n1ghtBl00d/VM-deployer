from ..extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(50), unique=True, nullable=False)
    password_hash   = db.Column(db.String(128), nullable=False)
    flags           = db.relationship('Flag', backref='user', lazy='dynamic')

    def __repr__(self):
        return self.username

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Flag(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    flag    = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return self.flag
    
# Changes
class Dungeon(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dugeon_level    = db.Column(db.String(128), nullable=False)
    boss            = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return {
            'dungeon' : self.dugeon_level,
            'level'   : self.level
        }
