#region imports
from flask import Flask, session, g
from flask_socketio import SocketIO
from flask_cors import CORS
from flask import Flask, render_template, request, redirect, url_for, make_response, Response
from ratelimit import limits, sleep_and_retry, RateLimitException
from .extensions import db
from .database import User, Flag, Machines, load_bosses, Templates
from .flask_config import default
from .utils import login_required, admin_required

import threading, os, time, subprocess, re, secrets, datetime

from .api import *
from .api_groups import *
from .config import *
from .deployGroups import Groups
#endregion import
#region global variables
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app, supports_credentials=True)
statusCache = []
#endregion global variables

app.config.from_object(default)

# Init Flask SQLAlchemy
db.init_app(app)

# Create database
with app.app_context():
    db.create_all()
    load_bosses()

# def heartBeat():
#     with app.app_context():
#         renewMachines()
#     print('HEART BEAT')
#     heartBeatThread = threading.Timer(3600, heartBeat)
#     heartBeatThread.start()

# heartBeat()
api_groups_init(socketio)

# Blueprint routes
from .routes import player, flag, admin, game_stats
app.register_blueprint(player, url_prefix='/api/player')
app.register_blueprint(flag, url_prefix='/api/flag')
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(game_stats, url_prefix='/api/game')

#region utilites
def heartBeat():
    while not heartBeat.cancelled:
        with app.app_context():
            renewMachines()
            renewTemplates()
        time.sleep(30)
    # proxmox.nodes.get()
    # print("heartbeat")
    # heartBeatThread = threading.Timer(3600, heartBeat)
    # heartBeatThread.start()

heartBeat.cancelled = False
# with app.app_context():
#     renewTemplates()
# t = threading.Thread(target=heartBeat)
# t.start()

def sendUpdateStatus(sid):
    machines = Machines.query.all()
    for machine in machines:
        machine = {
            "vmid": machine.machine_id, 
            "name": machine.machine_name, 
            "status": "Running" if machine.ip != "n/a" else "Offline",
            "ip": machine.ip,
            "vncStatus": "LATER",
            "username": machine.username
        }
        socketio.emit("vmListEntry", machine, room=sid)

@sleep_and_retry
@limits(calls=3, period=10) # Max 3 calls per 10 seconds
def updateStatusWrapper(vmid, sid, username='darkon3', template_id=0):
    print('UPDATE', flush=True)
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        g.proxmox_node = user.node
        lxcs = getLXCs()
        vms = getVMs()
        statusEntry = ""
        print('ALL', lxcs, flush=True)
        if vmid in lxcs:
            statusEntry = updateStatusLXC(vmid)
            print('STATUS', statusEntry, flush=True)
        if vmid in vms:
            statusEntry = updateStatusVM(vmid)
        if not statusEntry:
            socketio.emit("vmListEntry", {"vmid": "ERROR", "name": "", "status": "", "ip": "ASK HELP", "vncStatus": ""}, room=sid)
            return
        socketio.emit("vmListEntry", {"vmid": statusEntry["vmid"], "name": statusEntry["name"], "status": statusEntry["status"], "ip": statusEntry["ipAddr"], "vncStatus": statusEntry["vncStatus"]}, room=sid)
        if template_id != 0:
            user_machine = Machines(
                username        = username,
                template_id     = template_id,
                machine_id      = vmid,
                ip              = statusEntry["ipAddr"],
                machine_name    = statusEntry["name"],
                cluster_node    = g.proxmox_node,
                created         = datetime.datetime.now(),
                type            = statusEntry['type']
            )
            print('SAVING', flush=True)
            db.session.add(user_machine)
            db.session.commit()
            socketio.emit("singleVmEntry", {"status": "Running", "ip": statusEntry["ipAddr"]}, room=sid)

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
    
def updateStatusCached(vmid, sid):
    for entry in statusCache:
        if (entry["vmid"] == vmid):
            if (entry["updateTime"] < datetime.datetime.now()-datetime.timedelta(minutes=60)):
                updateStatusWrapper(vmid, sid)
            elif (entry["statusEntry"]["ipAddr"] == "n/a"):
                updateStatusWrapper(vmid, sid)
            else:
                statusEntry = entry["statusEntry"]
                socketio.emit("vmListEntry", {"vmid": statusEntry["vmid"], "name": statusEntry["name"], "status": statusEntry["status"], "ip": statusEntry["ipAddr"], "vncStatus": statusEntry["vncStatus"]}, room=sid)
            break
    else:
        updateStatusWrapper(vmid, sid)
#endregion utilities  

#region Flask routes
@app.route("/")
def hello_world():
    return render_template('index.html', CLONE_RANGE_LOWER =CLONE_RANGE_LOWER, CLONE_RANGE_UPPER =CLONE_RANGE_UPPER)

@app.route("/vnc")
@admin_required
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
@admin_required
def getTemplates(data):
    all_templates = []
    print("TEMPLATES", flush=True)
    templates = Templates.query.all()
    print("TEMPLATES", templates, flush=True)
    # In case we want to do a forced update
    try:
        force_update_templates = data.get('forceTemplates', False)
    except:
        force_update_templates = False

    if not templates or force_update_templates:
        renewTemplates()
    else:
        for template in templates:
            all_templates.append({
                "vmid": template.template_id,
                "name": template.template_name
            })
    
    socketio.emit("TemplateList", all_templates)

@socketio.on("cloneTemplate")
@login_required
def cloneTemplate(data):
    templateId = int(data)
    username = session['username'] # for testing reasons
    user = User.query.filter_by(username=username).first()
    g.proxmox_node = user.node
    machine = getUserMachine(username, templateId)
    if machine and session.get('role', 'user') != 'admin':
       socketio.emit("statusUpdate", {"status": "Running", "ip": machine["ip"]}, room=request.sid)
       return

    nextid = getNextId()
    # This will need to be updated so it doesn't return ALL machines to user
    socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid}, room=request.sid)
    newid = create(templateId, nextid, username)
    socketio.emit("statusUpdate", {"status": "Starting VM", "newID": nextid}, room=request.sid)
    start(newid)
    socketio.emit("statusUpdate", {"status": "VM Online", "newID": nextid}, room=request.sid)
    statusThread = threading.Timer(15, updateStatusWrapper, args=[newid, request.sid, username, templateId])
    statusThread.start()
    

@socketio.on("delAll")
@admin_required
def delAll(data):
    lxcs = getLXCs(admin_all=True)
    vms = getVMs(admin_all=True)
    for lxc in lxcs:
        socketio.emit("statusUpdate", {"status": "Deleting", "newID": lxc}, room=request.sid)
        deleteLXC(lxc)
        socketio.emit("statusUpdate", {"status": "Deleted", "newID": lxc}, room=request.sid)
    for vm in vms:
        socketio.emit("statusUpdate", {"status": "Deleting", "newID": vm}, room=request.sid)
        deleteVM(vm)
        socketio.emit("statusUpdate", {"status": "Deleted", "newID": vm}, room=request.sid)

@socketio.on("updateUsersBoxes")
@login_required
def updateBoxSatus():
    username = session['username']
    users_machines = Machines.query.filter_by(username=username).all()
    machines = []
    for machine in users_machines:
        machines.append({
            'ip': machine.ip,
            'name': machine.machine_name
        })

    socketio.emit("userVmList", machines, room=request.sid)

@socketio.on("updateAllStatus")
@admin_required
def updateAllStatus(data):
    sendUpdateStatus(request.sid)

@socketio.on("ForceUpdateAllStatus")
@admin_required
def updateAllStatus(data):
    with app.app_context():
        renewMachines()
        sendUpdateStatus(request.sid)


@socketio.on("deleteVM")
@admin_required
def handleDelete(data):
    vmid = data['vmid']
    machine = Machines.query.filter_by(machine_id=vmid).first()
    if machine is None:
        return
    g.proxmox_node = machine.cluster_node
    delete(vmid)
    socketio.emit("statusUpdate", {"status": "Deleted", "newID": vmid}, room=request.sid)

@socketio.on("revertState")
@login_required
def revertState(data):
    vmid = data['vmid']
    role = session.get('role', 'user')
    username = session['username']
    machine_type = None
    if role == 'admin':
        user_machine = Machines.query.filter_by(machine_id=vmid).first()
        if not user_machine:
            return
    else:
        user_machine = Machines.query.filter_by(username=username, template_id=vmid).first()
        if not user_machine:
            return
        
    g.proxmox_node = user_machine.cluster_node
    machine_type = user_machine.type
    machine_id = user_machine.machine_id

    socketio.emit("statusUpdate", {"status": "Reverting to Initial State", "newID": vmid}, room=request.sid)
    revert(machine_id, machine_type, role)
    socketio.emit("statusUpdate", {"status": "Reverted to Initial State", "newID": vmid, "ip": user_machine.ip}, room=request.sid)

@socketio.on("reboot")
@login_required
def socket_reboot(data):
    print('printing stuff', data)
    vmid = data.get('vmid', 0)
    role = session.get('role', 'user')
    username = session['username']
    machine_type = None
    if role == 'admin':
        user_machine = Machines.query.filter_by(machine_id=vmid).first()
        if not user_machine:
            return
    else:
        user_machine = Machines.query.filter_by(username=username, template_id=vmid).first()
        if not user_machine:
            return
        
    g.proxmox_node = user_machine.cluster_node
    machine_type = user_machine.type
    machine_id = user_machine.machine_id

    socketio.emit("statusUpdate", {"status": "Rebooting", "newID": vmid}, room=request.sid)
    reboot(machine_id, machine_type, role)
    socketio.emit("statusUpdate", {"status": "Rebooted", "newID": vmid, "ip": user_machine.ip}, room=request.sid)

@socketio.on("addFirewallEntry")
@admin_required
def addFirewallEntry(data):
    print("entered addFirewallEntry()")
    print(data)
    vmid = int(data["vmid"])
    ipAddr = data["ipAddr"]
    print(f"vmid: {vmid}, ipAddr: {ipAddr}")
    enableFirewall(vmid)
    addFirewallAllowedIP(vmid, ipAddr)
#endregion individual actions

#region all user actions
@socketio.on("announcementMessage")
@admin_required
def send_message_all(data):
    print(data)

    if not data:
        return
    print('Sending', data)
    socketio.emit("announcement", {"message": data})
#endregion all user actions

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