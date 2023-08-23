from ..extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


# Struct
# {
#     "dungeonOne": {
#         "boss": {
#             "Gnu": {
#                 "key": true,
#                 "isDead": true,
#                 "details": {
#                     "description" : "",
#                     "vmid": 12,
#                     "strengths": "",
#                     "weaknesses": "",
#                     "bossGraphicKey": "gnu"
#                 }
#             },
#             "Gnu2": {
#                 "key": true,
#                 "isDead": true,
#                 "details": {
#                     "description" : "",
#                     "vmid": 12,
#                     "strengths": "",
#                     "weaknesses": "",
#                     "bossGraphicKey": "gnu"
#                 }
#             },
#             "Gnu3": {
#                 "key": false,
#                 "isDead": false,
#                 "details": {
#                     "description" : "",
#                     "vmid": 12,
#                     "strengths": "",
#                     "weaknesses": "",
#                     "bossGraphicKey": "gnu"
#                 }
#             }
#         }
#     }
# }



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

class Boss_Info(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    level           = db.Column(db.String(50), nullable=False)
    boss            = db.Column(db.String(256), nullable=False)
    description     = db.Column(db.String(256), nullable=False)
    vmid            = db.Column(db.Integer, nullable=False)
    strengths       = db.Column(db.String(256), nullable=False)
    weaknesses      = db.Column(db.String(256), nullable=False)
    bossGraphicKey  = db.Column(db.String(256), nullable=False)


    def __repr__(self):
        return self.user_id
    
# class Boss_

class Flag(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    level   = db.Column(db.String(50), nullable=False)
    boss    = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return self.user_id

class Check_Flag(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    flag    = db.Column(db.String(100), nullable=False)
    level   = db.Column(db.String(100), nullable=False)
    boss    = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return self.flag
    
    # def check_flag(self, flag, level)
# Changes
class Dungeon(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level           = db.Column(db.String(128), nullable=False)
    boss            = db.Column(db.String(256), nullable=False)
    key             = db.Column(db.Boolean, nullable=False)
    is_dead         = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return {
            'dungeon' : self.dugeon_level,
            'level'   : self.level
        }
