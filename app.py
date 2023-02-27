from flask import Flask
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for, make_response, Response

import threading, os, time, subprocess, re, secrets

from api import *

app = Flask(__name__)
socketio = SocketIO(app) 


heartBeat()

def updateStatusWrapper(vmid):
    lxcs = getLXCs()
    vms = getVMs()
    status = ""
    ipAddr = ""
    vncEnabled = False
    if vmid in lxcs:
        status, ipAddr = updateStatusLXC(vmid)
    if vmid in vms:
        status, ipAddr, vncEnabled = updateStatusVM(vmid)
    #print(f"statusUpdate: {vmid} is {status['name']} - {ipAddr}")
    socketio.emit("vmListEntry", {"vmid": vmid, "name": status["name"], "status": status["status"], "ip": ipAddr, "vncStatus": vncEnabled})    
    


@app.route("/")
def hello_world():
    return render_template('index.html')

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
    id = int(data)
    lxcs = getTemplateLXCs()
    nextid = getNextId()
    if id in lxcs:
        socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
        newid = createLXC(id, nextid)
        socketio.emit("statusUpdate", {"status": "Starting VM", "newID": nextid})
        startLXC(newid)
        socketio.emit("statusUpdate", {"status": "VM Online", "newID": nextid})
        statusThread = threading.Timer(15, updateStatusWrapper, args=[newid])
        statusThread.start
    else:
        socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
        newid = createVM(id, nextid)
        socketio.emit("statusUpdate", {"status": "Starting VM", "newID": nextid})
        startVM(newid)
        socketio.emit("statusUpdate", {"status": "VM Online", "newID": nextid})
        statusThread = threading.Timer(15, updateStatusWrapper, args=[newid])
        statusThread.start

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
        statusThread = threading.Thread(target=updateStatusWrapper, args=[lxc])
        statusThread.start()
    for vm in vms:
        statusThread = threading.Thread(target=updateStatusWrapper, args=[vm])
        statusThread.start()

@socketio.on("deleteVM")
def handleDelete(data):
    vmid = data['vmid']
    lxcs = getLXCs()
    vms = getVMs()
    if vmid in lxcs:
        deleteLXC(vmid)
    if vmid in vms:
        deleteVM(vmid)

@socketio.on("revertState")
def revertState(data):
    vmid = data['vmid']
    socketio.emit("statusUpdate", {"status": "Reverting to Initial State", "newID": vmid})
    lxcs = getLXCs()
    vms = getVMs()
    if vmid in lxcs:
        revertLXC(vmid)
    if vmid in vms:
        revertVM(vmid)
    socketio.emit("statusUpdate", {"status": "Reverted to Initial State", "newID": vmid})
    

@socketio.on("reboot")
def revertState(data):
    vmid = data['vmid']
    socketio.emit("statusUpdate", {"status": "Rebooting", "newID": vmid})
    lxcs = getLXCs()
    vms = getVMs()
    if vmid in lxcs:
        rebootLXC(vmid)
    if vmid in vms:
        rebootVM(vmid)
    socketio.emit("statusUpdate", {"status": "Rebooted", "newID": vmid})
