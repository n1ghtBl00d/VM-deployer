#region imports
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask import Flask, render_template, request, redirect, url_for, make_response, Response
from ratelimit import limits, sleep_and_retry, RateLimitException
from .extensions import db
from .database import User, Flag, Dungeon, load_bosses
from .flask_config import default

import threading, os, time, subprocess, re, secrets, datetime

from .api import *
from .api_groups import *
from .config import *
from .deployGroups import Groups
#endregion import
#region global variables
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)
statusCache = []
#endregion global variables

app.config.from_object(default)

# Init Flask SQLAlchemy
db.init_app(app)

# Create database
with app.app_context():
    db.create_all()
    load_bosses()

heartBeat()
api_groups_init(socketio)

# Blueprint routes
from .routes import player, flag, admin, game_stats
app.register_blueprint(player, url_prefix='/player')
app.register_blueprint(flag, url_prefix='/flag')
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(game_stats, url_prefix='/game')

#region utilites
@sleep_and_retry
@limits(calls=3, period=10) # Max 3 calls per 10 seconds
def updateStatusWrapper(vmid):
    lxcs = getLXCs()
    vms = getVMs()
    statusEntry = ""
    if vmid in lxcs:
        statusEntry = updateStatusLXC(vmid)
    if vmid in vms:
        statusEntry = updateStatusVM(vmid)
    socketio.emit("vmListEntry", {"vmid": statusEntry["vmid"], "name": statusEntry["name"], "status": statusEntry["status"], "ip": statusEntry["ipAddr"], "vncStatus": statusEntry["vncStatus"]})

    for entry in statusCache:
        if (entry["vmid"] == vmid):
            entry["statusEntry"] = statusEntry
            entry["updateTime"] = datetime.datetime.now()
            break
    else:
        statusCache.append({
            "vmid": vmid,
            "statusEntry": statusEntry,
            "updateTime": datetime.datetime.now()
        })
    
def updateStatusCached(vmid):
    for entry in statusCache:
        if (entry["vmid"] == vmid):
            if (entry["updateTime"] < datetime.datetime.now()-datetime.timedelta(minutes=60)):
                updateStatusWrapper(vmid)
            elif (entry["statusEntry"]["ipAddr"] == "n/a"):
                updateStatusWrapper(vmid)
            else:
                statusEntry = entry["statusEntry"]
                socketio.emit("vmListEntry", {"vmid": statusEntry["vmid"], "name": statusEntry["name"], "status": statusEntry["status"], "ip": statusEntry["ipAddr"], "vncStatus": statusEntry["vncStatus"]})
            break
    else:
        updateStatusWrapper(vmid)
#endregion utilities  

#region Flask routes
@app.route("/")
def hello_world():
    return render_template('index.html', CLONE_RANGE_LOWER =CLONE_RANGE_LOWER, CLONE_RANGE_UPPER =CLONE_RANGE_UPPER)

@app.route("/vnc")
def vncConnect():
    vmid = int(request.args.get("vmid"))
    ports = getVNCports()
    if(vmid == None):
        return redirect("/")
    
    for entry in ports:
        if entry["vmid"] == vmid:
            port = entry["port"] + 5900
            break
    else: #If no break in For loop (No matching entry in ports)
        return redirect("/")

    PASSWORD = secrets.token_urlsafe(8)
    VNC_REDIRECT_URL = f"http://{NOVNC_IP}:{NOVNC_PORT}/vnc.html?autoconnect=true&resize=scale&show_dot=true&"
    setVNCPassword(vmid, PASSWORD)
    return redirect(f"{VNC_REDIRECT_URL}path=vnc%2F{PROXMOX_IP}%2F{port}&password={PASSWORD}")
#endregion Flask routes

#region SocketIO event Channels 

#region Individual actions
@socketio.on("getTemplates")
def getTemplates(data):
    templates = getAllTemplates()
    socketio.emit("TemplateList", templates)

@socketio.on("cloneTemplate")
def cloneTemplate(data):
    templateId = int(data)
    nextid = getNextId()
    socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
    newid = create(templateId, nextid)
    socketio.emit("statusUpdate", {"status": "Starting VM", "newID": nextid})
    start(newid)
    socketio.emit("statusUpdate", {"status": "VM Online", "newID": nextid})
    statusThread = threading.Timer(15, updateStatusWrapper, args=[newid])
    statusThread.start()
    

@socketio.on("delAll")
def delAll(data):
    lxcs = getLXCs()
    vms = getVMs()
    for lxc in lxcs:
        socketio.emit("statusUpdate", {"status": "Deleting", "newID": lxc})
        deleteLXC(lxc)
        socketio.emit("statusUpdate", {"status": "Deleted", "newID": lxc})
    for vm in vms:
        socketio.emit("statusUpdate", {"status": "Deleting", "newID": vm})
        deleteVM(vm)
        socketio.emit("statusUpdate", {"status": "Deleted", "newID": vm})

@socketio.on("updateAllStatus")
def updateAllStatus(data):
    lxcs = getLXCs()
    vms = getVMs()
    for lxc in lxcs:
        statusThread = threading.Thread(target=updateStatusCached, args=[lxc])
        statusThread.start()
    for vm in vms:
        statusThread = threading.Thread(target=updateStatusCached, args=[vm])
        statusThread.start()

@socketio.on("ForceUpdateAllStatus")
def updateAllStatus(data):
    lxcs = getLXCs()
    vms = getVMs()
    for lxc in lxcs:
        statusThread = threading.Thread(target=updateStatusWrapper, args=[lxc])
        statusThread.start()
    for vm in vms:
        statusThread = threading.Thread(target=updateStatusWrapper, args=[vm])
        statusThread.start()

@socketio.on("deleteVM")
def handleDelete(data):
    vmid = data['vmid']
    delete(vmid)
    socketio.emit("statusUpdate", {"status": "Deleted", "newID": vmid})

@socketio.on("revertState")
def revertState(data):
    vmid = data['vmid']
    socketio.emit("statusUpdate", {"status": "Reverting to Initial State", "newID": vmid})
    revert(vmid)
    socketio.emit("statusUpdate", {"status": "Reverted to Initial State", "newID": vmid})

@socketio.on("reboot")
def reboot(data):
    vmid = data['vmid']
    socketio.emit("statusUpdate", {"status": "Rebooting", "newID": vmid})
    reboot(vmid)
    socketio.emit("statusUpdate", {"status": "Rebooted", "newID": vmid})

@socketio.on("addFirewallEntry")
def addFirewallEntry(data):
    print("entered addFirewallEntry()")
    print(data)
    vmid = int(data["vmid"])
    ipAddr = data["ipAddr"]
    print(f"vmid: {vmid}, ipAddr: {ipAddr}")
    enableFirewall(vmid)
    addFirewallAllowedIP(vmid, ipAddr)
#endregion individual actions

#region group actions
@socketio.on("getGroups")
def getTemplates(data):
    groupList = []
    for index, group in enumerate(Groups):
        groupList.append({"groupID": index, "groupName": group["groupName"]})
    socketio.emit("groupList", groupList)
    
@socketio.on("cloneGroup")
def runCloneGroup(data):
    groupID = int(data)
    cloneGroup(Groups[groupID])
#endregion group actions

#endregion SocketIO event channels