from .database import Boss_Info
from ..extensions import db


all_bosses_info = [
    {
        "level": "dungeonOne",
        "boss": "Gnu",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonOne",
        "boss": "Gnu2",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonOne",
        "boss": "Gnu3",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },    {
        "level": "dungeonTwo",
        "boss": "Gnu4",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonTwo",
        "boss": "Gnu5",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonTwo",
        "boss": "Gnu6",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },    {
        "level": "dungeonThree",
        "boss": "Gnu7",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonThree",
        "boss": "Gnu8",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonThree",
        "boss": "Gnu9",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },    {
        "level": "dungeonFour",
        "boss": "Gnu10",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonFour",
        "boss": "Gnu11",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonFour",
        "boss": "Gnu12",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },    {
        "level": "dungeonFive",
        "boss": "Gnu13",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonFive",
        "boss": "Gnu14",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    },{
        "level": "dungeonFive",
        "boss": "Gnu15",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "bossGraphicKey": "gnu"
    }
]


def load_bosses():
    bosses = []
    for boss_info in all_bosses_info:
        try:
            boss = Boss_Info(**boss_info)
            db.session.add(boss)
            db.session.commit()
        except Exception as e:
            db.session.rollback()

 