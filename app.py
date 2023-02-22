from flask import Flask
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for, make_response, Response

import threading, os, time, subprocess, re

from api import *

app = Flask(__name__)
socketio = SocketIO(app) 


heartBeat()

def updateStatusWrapper(vmid):
    lxcs = getLXCs()
    vms = getVMs()
    status = ""
    ipAddr = ""
    if vmid in lxcs:
        status, ipAddr = updateStatusLXC(vmid)
    if vmid in vms:
        status, ipAddr = updateStatusVM(vmid)
    socketio.emit("vmListEntry", {"vmid": vmid, "name": status["name"], "status": status["status"], "ip": ipAddr})    
    


@app.route("/")
def hello_world():
    return render_template('index.html')

@socketio.on("getTemplates")
def getTemplates(data):
    print("getTemplates")
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
    print(f'data: {data}')
    vmid = data['vmid']
    print(f'vmid: {vmid}')
    lxcs = getLXCs()
    vms = getVMs()
    print("got lists")
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
