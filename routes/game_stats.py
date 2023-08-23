from flask import Blueprint, session, request
from ..extensions import db
from ..database import User, Flag, Check_Flag, Bosses, Dungeon, Boss_Info
from ..utils import login_required


game_stats = Blueprint('game_stats', __name__)


@game_stats.get('/game/<string:level>')
@login_required
def get_game_stats(level):
    boss_info = Boss_Info.query.filter_by(level=level)
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if not user:
        return {'Error': 'No user'}, 404
    
    game_stats = {}
    dungeon_stats = Dungeon.query.filter_by(user_id=user.id, level=level)

    if not dungeon_stats:
        bosses = []
        for boss in boss_info:
            bosses.append(Dungeon(user_id=user.id, level=level, boss=boss.boss, key=False, is_dead=False))
            game_stats[boss.boss] = {
                "key"     : False,
                "id_dead" : False,
                "details" : {}
            }
        
        db.session.bulk_save_objects(bosses)
        db.session.commit()
    else:
        for dungeon_stat in dungeon_stats:
            game_stats[dungeon_stat.boss] = {
                "key"     : dungeon_stat.key,
                "id_dead" : dungeon_stat.is_dead,
                "details" : {}
            }
    
    for info in boss_info:
        game_stats[info.boss]['details'] = {
            "description" : info.description,
            "vmid" : info.vmid,
            "strengths" : info.strengths,
            "weaknesses" : info.weaknesses,
            "bossGraphicKey" : info.bossGraphicKey
        }

    return {level : game_stats}, 200