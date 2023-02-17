from flask import Flask
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for, make_response, Response
from proxmoxer import ProxmoxAPI
import threading, os, time, subprocess, re

from config import API_URL, API_PORT, SSL_VERIFY, API_USERNAME, API_PASSWORD, SSH_ENABLE, PROXMOX_NODE, VM_POOL, TEMPLATE_RANGE_LOWER, TEMPLATE_RANGE_UPPER, CLONE_RANGE_LOWER, CLONE_RANGE_UPPER


ipPattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
macPattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')


proxmox = ProxmoxAPI(
    API_URL, user=API_USERNAME, password=API_PASSWORD, verify_ssl=SSL_VERIFY, port=API_PORT
)

def heartBeat():
    proxmox.nodes.get()
    print("heartbeat")
    heartBeatThread = threading.Timer(3600, heartBeat)
    heartBeatThread.start()

def getLXCs():
    lxcs = []
    for lxc in proxmox.nodes(PROXMOX_NODE).lxc.get():
        lxcs.append(int(lxc["vmid"]))
    lxcs[:] = [x for x in lxcs if (x >= CLONE_RANGE_LOWER and x <= CLONE_RANGE_UPPER)]
    lxcs.sort()
    return lxcs

def getVMs():
    vms = []
    for vm in proxmox.nodes(PROXMOX_NODE).qemu.get():
        vms.append(int(vm["vmid"]))
    vms[:] = [x for x in vms if (x >= CLONE_RANGE_LOWER and x <= CLONE_RANGE_UPPER)]
    vms.sort()
    return vms

def getTemplateLXCs():
    lxcs = []
    for lxc in proxmox.nodes(PROXMOX_NODE).lxc.get():
        lxcs.append(int(lxc["vmid"]))
    lxcs[:] = [x for x in lxcs if (x >= TEMPLATE_RANGE_LOWER and x <= TEMPLATE_RANGE_UPPER)]
    lxcs.sort()
    return lxcs

def getTemplateVMs():
    vms = []
    for vm in proxmox.nodes(PROXMOX_NODE).qemu.get():
        vms.append(int(vm["vmid"]))
    vms[:] = [x for x in vms if (x >= TEMPLATE_RANGE_LOWER and x <= TEMPLATE_RANGE_UPPER)]
    vms.sort()
    return vms

def getNameLXC(vmid):
    config = proxmox.nodes(PROXMOX_NODE).lxc(vmid).config.get()
    description = config["description"]
    name = description.partition('\n')[0][2:]
    print(name)
    return name

def getNameVM(vmid):
    config = proxmox.nodes(PROXMOX_NODE).qemu(vmid).config.get()
    description = config["description"]
    name = description.partition('\n')[0][2:]
    print(name)
    return name

def clean_string(string):
    cleaned = []
    for char in string:
        if char.isalnum():
            cleaned.append(char)
        elif char.isspace():
            cleaned.append("-")
        elif (char == '.'):
            cleaned.append(char)
    return "".join(cleaned)

def getAllTemplates():
    templates = []
    lxcs = getTemplateLXCs()
    vms = getTemplateVMs()
    for lxc in lxcs:
        templates.append({"vmid": lxc, "name": getNameLXC(lxc)})
    for vm in vms:
        templates.append({"vmid": vm, "name": getNameVM(vm)})
    socketio.emit("TemplateList", templates)


def getNextId():
    lxcs = getLXCs()
    vms = getVMs()
    ids = lxcs + vms
    if (ids == []):
        return CLONE_RANGE_LOWER
    else:
        for x in range(CLONE_RANGE_LOWER, CLONE_RANGE_UPPER):
            if x not in ids:
                return x


def checkStatus(task_id, new_id):
    data = {"status": ""}
    while (data["status"] != "stopped"):
        data = proxmox.nodes(PROXMOX_NODE).tasks(task_id).status.get()
        socketio.emit("statusUpdate", {"status": data, "newID": new_id})

def waitOnTask(task_id):
    data = {"status": ""}
    while (data["status"] != "stopped"):
        data = proxmox.nodes(PROXMOX_NODE).tasks(task_id).status.get()

def createAndStartLXC(cloneid, name="default"):
    nextid = getNextId()
    socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
    if(name == "default"):
        name = getNameLXC(cloneid)
    name = clean_string(name.strip())
    cloneTask = proxmox.nodes(PROXMOX_NODE).lxc(cloneid).clone.post(newid=nextid, node=PROXMOX_NODE, vmid=cloneid, pool=VM_POOL, hostname=name)
    waitOnTask(cloneTask)
    print("created")
    snapshotTask = proxmox.nodes(PROXMOX_NODE).lxc(nextid).snapshot.post(vmid=nextid, node=PROXMOX_NODE, snapname="initState")
    waitOnTask(snapshotTask)
    socketio.emit("statusUpdate", {"status": "Starting VM", "newID": nextid})
    startTask = proxmox.nodes(PROXMOX_NODE).lxc(nextid).status.start.post(node=PROXMOX_NODE, vmid=nextid)
    waitOnTask(startTask)
    print("Started")
    time.sleep(10)
    socketio.emit("statusUpdate", {"status": "VM Online", "newID": nextid})

    ipAddr = getIP(nextid)
    status = proxmox.nodes(PROXMOX_NODE).lxc(nextid).status.current.get()
    socketio.emit("vmListEntry", {"vmid": nextid, "name": status["name"], "status": status["status"], "ip": ipAddr})

def createAndStartVM(cloneid, name="default"):
    nextid = getNextId()
    socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
    if(name == "default"):
        name = getNameVM(cloneid)
    name = clean_string(name.strip())
    cloneTask = proxmox.nodes(PROXMOX_NODE).qemu(cloneid).clone.post(newid=nextid, node=PROXMOX_NODE, vmid=cloneid, pool=VM_POOL, name=name)
    waitOnTask(cloneTask)
    print("created")
    snapshotTask = proxmox.nodes(PROXMOX_NODE).qemu(nextid).snapshot.post(vmid=nextid, node=PROXMOX_NODE, snapname="initState")
    waitOnTask(snapshotTask)
    socketio.emit("statusUpdate", {"status": "Starting VM", "newID": nextid})
    startTask = proxmox.nodes(PROXMOX_NODE).qemu(nextid).status.start.post(node=PROXMOX_NODE, vmid=nextid)
    waitOnTask(startTask)
    print("Started")
    time.sleep(30)
    socketio.emit("statusUpdate", {"status": "VM Online", "newID": nextid})

    status = proxmox.nodes(PROXMOX_NODE).qemu(nextid).status.current.get()
    
    ipAddr = getIP(nextid) 
    socketio.emit("vmListEntry", {"vmid": nextid, "name": status["name"], "status": status["status"], "ip": ipAddr})
    
    
def deleteLXC(delId):
    status = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.current.get()
    if(status["status"] != "stopped"):
        socketio.emit("statusUpdate", {"status": "Shutting Down", "newID": delId})
        shutdownTask = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    socketio.emit("statusUpdate", {"status": "Deleting", "newID": delId})
    deleteTask = proxmox.nodes(PROXMOX_NODE).lxc(delId).delete()
    waitOnTask(deleteTask)
    socketio.emit("statusUpdate", {"status": "Deleted", "newID": delId})

def deleteVM(delId):
    status = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.current.get()
    if(status["status"] != "stopped"):
        socketio.emit("statusUpdate", {"status": "Shutting Down", "newID": delId})
        shutdownTask = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    socketio.emit("statusUpdate", {"status": "Deleting", "newID": delId})
    deleteTask = proxmox.nodes(PROXMOX_NODE).qemu(delId).delete()
    waitOnTask(deleteTask)
    socketio.emit("statusUpdate", {"status": "Deleted", "newID": delId})

def shutdownLXC(delId):
    status = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.current.get()
    if(status["status"] != "stopped"):
        socketio.emit("statusUpdate", {"status": "Shutting Down", "newID": delId})
        shutdownTask = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    socketio.emit("statusUpdate", {"status": "Shutdown Complete", "newID": delId})

def shutdownVM(delId):
    status = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.current.get()
    if(status["status"] != "stopped"):
        socketio.emit("statusUpdate", {"status": "Shutting Down", "newID": delId})
        shutdownTask = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    socketio.emit("statusUpdate", {"status": "Shutdown Complete", "newID": delId})


        

def deleteAll():
    lxcs = getLXCs()
    vms = getVMs()
    for lxc in lxcs:
        deleteLXC(lxc)
    for vm in vms:
        deleteVM(vm)


def getIP(vmid):
    lxcs = getLXCs()
    vms = getVMs()
    if vmid in lxcs:
        if SSH_ENABLE == True:
            command = "ssh proxmox lxc-ls -f | grep " + str(vmid)
            ipAddr = str(ipPattern.search(subprocess.check_output(command, shell=True).decode('utf-8'))[0])
        else:
            config = proxmox.nodes(PROXMOX_NODE).lxc(vmid).config.get()
            mac = str(macPattern.search(str(config))[0])
            command = "arp-scan -l | grep -i " + mac
            ipAddr = str(ipPattern.search(subprocess.check_output(command, shell=True).decode('utf-8'))[0])
        return ipAddr
    if vmid in vms:
        config = proxmox.nodes(PROXMOX_NODE).qemu(vmid).config.get()
        mac = str(macPattern.search(str(config))[0])
        command = "arp-scan -l | grep -i " + mac
        ipAddr = str(ipPattern.search(subprocess.check_output(command, shell=True).decode('utf-8'))[0])
        return ipAddr

    


app = Flask(__name__)
socketio = SocketIO(app)


heartBeat()


@app.route("/")
def hello_world():
    return render_template('index.html')

@socketio.on("getTemplates")
def getTemplates(data):
    getAllTemplates()

@socketio.on("cloneTemplate")
def cloneTemplate(data):
    id = int(data)
    lxcs = getTemplateLXCs()
    if id in lxcs:
        createThread = threading.Thread(target=createAndStartLXC, args=[id])
    else:
        createThread = threading.Thread(target=createAndStartVM, args=[id])
    createThread.start()

@socketio.on("delAll")
def delAll(data):
    delThread = threading.Thread(target=deleteAll)
    delThread.start()

@socketio.on("updateAllStatus")
def updateAllStatus(data):
    lxcs = getLXCs()
    for lxc in lxcs:
        status = proxmox.nodes(PROXMOX_NODE).lxc(lxc).status.current.get()
        if status["status"] == "running":
            ipAddr = getIP(lxc)
        else:
            ipAddr = "n/a"
        socketio.emit("vmListEntry", {"vmid": lxc, "name": status["name"], "status": status["status"], "ip": ipAddr})
    vms = getVMs()
    for vm in vms:
        status = proxmox.nodes(PROXMOX_NODE).qemu(vm).status.current.get()
        if status["status"] == "running":
            ipAddr = getIP(vm)   
        else:
            ipAddr = "n/a" 
        socketio.emit("vmListEntry", {"vmid": vm, "name": status["name"], "status": status["status"], "ip": ipAddr})

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
        revertTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).snapshot("initState").rollback.post(node=PROXMOX_NODE, vmid=vmid, snapname="initState")
        waitOnTask(revertTask)
        startTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
        waitOnTask(startTask)
    if vmid in vms:
        revertTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).snapshot("initState").rollback.post(node=PROXMOX_NODE, vmid=vmid, snapname="initState")
        waitOnTask(revertTask)
        startTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
        waitOnTask(startTask)
    socketio.emit("statusUpdate", {"status": "Reverted to Initial State", "newID": vmid})

@socketio.on("reboot")
def revertState(data):
    vmid = data['vmid']
    socketio.emit("statusUpdate", {"status": "Rebooting", "newID": vmid})
    lxcs = getLXCs()
    vms = getVMs()
    if vmid in lxcs:
        status = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.current.get()
        if status["status"] == "running":
            restartTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.reboot.post(node=PROXMOX_NODE, vmid=vmid)
            waitOnTask(restartTask)
        else:
            startTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
            waitOnTask(startTask)    
    if vmid in vms:
        status = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.current.get()
        if status["status"] == "running":
            restartTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.reboot.post(node=PROXMOX_NODE, vmid=vmid)
            waitOnTask(restartTask)
        else:
            startTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
            waitOnTask(startTask)
    socketio.emit("statusUpdate", {"status": "Rebooted", "newID": vmid})
