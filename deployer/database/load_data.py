from .database import Boss_Info, Check_Flag
from ..extensions import db


all_bosses_info = [
    {
        "level": "dungeonOne",
        "boss": "level11",
        "bossname": "Gnu",
        "description" : "",
        "vmid": 202,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "dragon"
    },{
        "level": "dungeonOne",
        "boss": "level12",
        "bossname": "Gnu2",
        "description" : "",
        "vmid": 204,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "bobmoss"
    },{
        "level": "dungeonOne",
        "boss": "level13",
        "bossname": "Gnu3",
        "description" : "",
        "vmid": 203,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "exa"
    },{
        "level": "dungeonOne",
        "boss": "level14",
        "bossname": "Gnu4",
        "description" : "",
        "vmid": 217,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "faerie"
    },     {
        "level": "dungeonTwo",
        "boss": "level21",
        "bossname": "Gnu5",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "golem"
    },{
        "level": "dungeonTwo",
        "boss": "level22",
        "bossname": "Gnu6",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "greenLighting"
    },{
        "level": "dungeonTwo",
        "boss": "level23",
        "bossname": "Gnu7",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "yellowLighting"
    },    {
        "level": "dungeonThree",
        "boss": "level31",
        "bossname": "Gnu8",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "tailor"
    },{
        "level": "dungeonThree",
        "boss": "level32",
        "bossname": "Gnu9",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "yabbo"
    },{
        "level": "dungeonThree",
        "boss": "level33",
        "bossname": "Gnu10",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "simon"
    },    {
        "level": "dungeonFour",
        "boss": "level41",
        "bossname": "Gnu11",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "bigears"
    },{
        "level": "dungeonFour",
        "boss": "level42",
        "bossname": "Gnu12",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "wormy"
    },{
        "level": "dungeonFour",
        "boss": "level43",
        "bossname": "Gnu13",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "seamoss"
    },    {
        "level": "dungeonFive",
        "boss": "level51",
        "bossname": "Gnu14",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "devilboy"
    },{
        "level": "dungeonFive",
        "boss": "level52",
        "bossname": "Gnu15",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "beetle"
    },{
        "level": "dungeonFive",
        "boss": "level53",
        "bossname": "Gnu16",
        "description" : "",
        "vmid": 12,
        "strengths": "",
        "weaknesses": "",
        "boss_graphic_key": "slimey"
    }
]

all_flags = {
    "level11": "TEST",
    "level12": "TEST",
    "level13": "TEST",
    "level14": "TEST",
    "level21": "TEST",
    "level22": "TEST",
    "level23": "TEST",
    "level31": "TEST",
    "level32": "TEST",
    "level33": "TEST",
    "level41": "TEST",
    "level42": "TEST",
    "level43": "TEST",
    "level51": "TEST",
    "level52": "TEST",
    "level53": "TEST",
}


def load_bosses():
    bosses = []
    for boss_info in all_bosses_info:
        try:
            boss = Boss_Info(**boss_info)
            flag = Check_Flag(flag=all_flags[boss_info['boss']], level=boss_info['level'], boss=boss_info['boss'])
            db.session.add(flag)
            db.session.add(boss)
            db.session.commit()
        except Exception as e:
            db.session.rollback()

 