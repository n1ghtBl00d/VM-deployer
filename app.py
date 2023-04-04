from flask import Flask
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for, make_response, Response
from ratelimit import limits, sleep_and_retry, RateLimitException

import threading, os, time, subprocess, re, secrets, datetime

from api import *


app = Flask(__name__)
socketio = SocketIO(app) 
statusCache = []


heartBeat()

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
  


@app.route("/")
def hello_world():
    return render_template('index.html', CLONE_RANGE_LOWER =CONFIG.CLONE_RANGE_LOWER, CLONE_RANGE_UPPER =CONFIG.CLONE_RANGE_UPPER)

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
    VNC_REDIRECT_URL = f"http://{CONFIG.NOVNC_IP}:{CONFIG.NOVNC_PORT}/vnc.html?autoconnect=true&resize=scale&show_dot=true&"
    setVNCPassword(vmid, PASSWORD)
    return redirect(f"{VNC_REDIRECT_URL}path=vnc%2F{CONFIG.PROXMOX_IP}%2F{port}&password={PASSWORD}")


    

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
