from flask import Flask
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for, make_response, Response
from proxmoxer import ProxmoxAPI
import threading, os, time, subprocess, re

from config import API_URL, API_PORT, API_USERNAME, API_PASSWORD, VM_TEMPLATE_ID, LXC_TEMPLATE_ID, SSH_ENABLE, PROXMOX_NODE

ID_RANGE_LOWER = 300
ID_RANGE_UPPER = 400

ipPattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
macPattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')


proxmox = ProxmoxAPI(
    API_URL, user=API_USERNAME, password=API_PASSWORD, verify_ssl=SSH_ENABLE, port=API_PORT
)

def getLXCs():
    lxcs = []
    for lxc in proxmox.nodes(PROXMOX_NODE).lxc.get():
        lxcs.append(int(lxc["vmid"]))
    lxcs[:] = [x for x in lxcs if (x >= ID_RANGE_LOWER and x <= ID_RANGE_UPPER)]
    lxcs.sort()
    return lxcs

def getVMs():
    vms = []
    for vm in proxmox.nodes(PROXMOX_NODE).qemu.get():
        vms.append(int(vm["vmid"]))
    vms[:] = [x for x in vms if (x >= ID_RANGE_LOWER and x <= ID_RANGE_UPPER)]
    vms.sort()
    return vms

def getNextId():
    lxcs = getLXCs()
    vms = getVMs()
    ids = lxcs + vms
    if (ids == []):
        return ID_RANGE_LOWER
    else:
        for x in range(ID_RANGE_LOWER, ID_RANGE_UPPER):
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

def createAndStartLXC(cloneid):
    nextid = getNextId()
    socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
    cloneTask = proxmox.nodes(PROXMOX_NODE).lxc(cloneid).clone.post(newid=nextid, node=PROXMOX_NODE, vmid=cloneid)
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

def createAndStartVM(cloneid):
    nextid = getNextId()
    socketio.emit("statusUpdate", {"status": "Creating VM", "newID": nextid})
    cloneTask = proxmox.nodes(PROXMOX_NODE).qemu(cloneid).clone.post(newid=nextid, node=PROXMOX_NODE, vmid=cloneid)
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

@app.route("/")
def hello_world():
    retString = "<p>LXCs:</p>"
    for lxc in proxmox.nodes(PROXMOX_NODE).lxc.get():
        id = lxc["vmid"]
        name = lxc["name"]
        
        
        retString += f"<p>{id}:  {name}</p>"
    lxcs = getLXCs()
    nextID = getNextId()
    retString += f"<br /><p>{lxcs}</p>"
    retString += f"<br /><p>{nextID}</p>"
    return retString

@app.route("/test")
def test():
    return render_template('index.html')

@socketio.on("newVM")
def newVM(data):
    createThread = threading.Thread(target=createAndStartVM, args=[VM_TEMPLATE_ID])
    createThread.start()

@socketio.on("newLXC")
def newVM(data):
    createThread = threading.Thread(target=createAndStartLXC, args=[LXC_TEMPLATE_ID])
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