from proxmoxer import ProxmoxAPI
import threading, os, time, subprocess, re, urllib.parse, datetime

import config as CONFIG 

arpResult = {
    "result": "resultString",
    "updateTime": datetime.datetime.now()
}

ipPattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
macPattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
vncPattern = re.compile(r':\s*(\d*)')


proxmox = ProxmoxAPI(
    CONFIG.API_URL, user=CONFIG.API_USERNAME, password=CONFIG.API_PASSWORD, verify_ssl=CONFIG.SSL_VERIFY, port=CONFIG.API_PORT
)

def heartBeat():
    proxmox.nodes.get()
    print("heartbeat")
    heartBeatThread = threading.Timer(3600, heartBeat)
    heartBeatThread.start()

def getLXCs():
    lxcs = []
    for lxc in proxmox.nodes(CONFIG.PROXMOX_NODE).lxc.get():
        lxcs.append(int(lxc["vmid"]))
    lxcs[:] = [x for x in lxcs if (x >= CONFIG.CLONE_RANGE_LOWER and x <= CONFIG.CLONE_RANGE_UPPER)]
    lxcs.sort()
    return lxcs

def getVMs():
    vms = []
    for vm in proxmox.nodes(CONFIG.PROXMOX_NODE).qemu.get():
        vms.append(int(vm["vmid"]))
    vms[:] = [x for x in vms if (x >= CONFIG.CLONE_RANGE_LOWER and x <= CONFIG.CLONE_RANGE_UPPER)]
    vms.sort()
    return vms

def getVNCports():
    ports = []
    for vm in proxmox.nodes(CONFIG.PROXMOX_NODE).qemu.get():
        vmid = int(vm["vmid"])
        config = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).config.get() #Get ports from all vms, not just clones
        if("args" in config.keys()):
            args = config["args"]
            port = str(vncPattern.search(args)[1])
            ports.append({"vmid": vmid, "port": int(port)})
    return ports

def checkTemplateVNC(templateId):
    config = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(templateId).config.get()
    description = config["description"]
    if "[!ENABLE_VNC]" in description:
        return True
    else:
        return False

def getTemplateLXCs():
    lxcs = []
    for lxc in proxmox.nodes(CONFIG.PROXMOX_NODE).lxc.get():
        lxcs.append(int(lxc["vmid"]))
    lxcs[:] = [x for x in lxcs if (x >= CONFIG.TEMPLATE_RANGE_LOWER and x <= CONFIG.TEMPLATE_RANGE_UPPER)]
    lxcs.sort()
    return lxcs

def getTemplateVMs():
    vms = []
    for vm in proxmox.nodes(CONFIG.PROXMOX_NODE).qemu.get():
        vms.append(int(vm["vmid"]))
    vms[:] = [x for x in vms if (x >= CONFIG.TEMPLATE_RANGE_LOWER and x <= CONFIG.TEMPLATE_RANGE_UPPER)]
    vms.sort()
    return vms

def getNameLXC(vmid):
    config = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).config.get()
    description = config["description"]
    name = description.partition('\n')[0][2:]
    return name

def getNameVM(vmid):
    config = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).config.get()
    description = config["description"]
    name = description.partition('\n')[0][2:]
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
    return templates


def getNextId():
    lxcs = getLXCs()
    vms = getVMs()
    ids = lxcs + vms
    if (ids == []):
        return CONFIG.CLONE_RANGE_LOWER
    else:
        for x in range(CONFIG.CLONE_RANGE_LOWER, CONFIG.CLONE_RANGE_UPPER):
            if x not in ids:
                return x

def getNextVncPort():
    ports = getVNCports()
    if(ports == []):
        return 1
    else:
        for x in range(1, 99):
            if not any((p["port"]) == x for p in ports):
                return x


def getIP(vmid):
    lxcs = getLXCs()
    vms = getVMs()
    if vmid in lxcs:
        config = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).config.get()
        mac = str(macPattern.search(str(config))[0])
    if vmid in vms:
        config = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).config.get()
        mac = str(macPattern.search(str(config))[0])
    return findIPbyMac(mac)

def findIPbyMac(mac):
    mac = mac.lower()
    now = datetime.datetime.now()
    if (arpResult["updateTime"] < now-datetime.timedelta(seconds=60)):
        arpResult["result"] = str(subprocess.check_output("arp-scan -l", shell=True).decode('utf-8')).lower()
        arpResult["updateTime"] = datetime.datetime.now()
    results = arpResult["result"].split("\n")
    for result in results:
        if mac in result:
            return str(ipPattern.search(result)[0])
    
    #If not found, try again but force arp scan
    arpResult["result"] = str(subprocess.check_output("arp-scan -l", shell=True).decode('utf-8')).lower()
    arpResult["updateTime"] = datetime.datetime.now()
    results = arpResult["result"].split("\n")
    for result in results:
        #print(result)
        if mac in result:
            return str(ipPattern.search(result)[0])
    
    #If not found
    return "Not Found"


def waitOnTask(task_id):
    data = {"status": ""}
    while (data["status"] != "stopped"):
        data = proxmox.nodes(CONFIG.PROXMOX_NODE).tasks(task_id).status.get()


def updateStatusLXC(lxc):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(lxc).status.current.get()
    if status["status"] == "running":
        ipAddr = getIP(lxc)
    else:
        ipAddr = "n/a"
    statusEntry = {
        "vmid": lxc,
        "name": status["name"],
        "status": status["status"],
        "ipAddr": ipAddr,
        "vncStatus": False,
        "lastUpdate": datetime.datetime.now()
    }
    return statusEntry

def updateStatusVM(vm):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vm).status.current.get()
    vncPorts = getVNCports()
    vncEnabled = False
    for entry in vncPorts:
        if entry["vmid"] == vm:
            vncEnabled = True
            break
    if status["status"] == "running":
        ipAddr = getIP(vm)   
    else:
        ipAddr = "n/a" 
    statusEntry = {
        "vmid": vm,
        "name": status["name"],
        "status": status["status"],
        "ipAddr": ipAddr,
        "vncStatus": vncEnabled,
        "lastUpdate": datetime.datetime.now()
    }
    return statusEntry

def createLXC(cloneid, newId, name="default"):
    if(name == "default"):
        name = getNameLXC(cloneid)
    name = clean_string(name.strip())
    cloneTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(cloneid).clone.post(newid=newId, node=CONFIG.PROXMOX_NODE, vmid=cloneid, pool=CONFIG.VM_POOL, hostname=name)
    waitOnTask(cloneTask)
    snapshotTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(newId).snapshot.post(vmid=newId, node=CONFIG.PROXMOX_NODE, snapname="initState")
    waitOnTask(snapshotTask)
    return newId

def createVM(cloneid, newId, name="default", vnc=None):
    if(name == "default"):
        name = getNameVM(cloneid)
    name = clean_string(name.strip())
    if(vnc == None):
        vnc = checkTemplateVNC(cloneid)
    cloneTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(cloneid).clone.post(newid=newId, node=CONFIG.PROXMOX_NODE, vmid=cloneid, pool=CONFIG.VM_POOL, name=name)
    waitOnTask(cloneTask)
    if(vnc == True):
        setupVNC(newId)
    snapshotTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(newId).snapshot.post(vmid=newId, node=CONFIG.PROXMOX_NODE, snapname="initState")
    waitOnTask(snapshotTask)
    return newId

def startLXC(vmid):
    startTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).status.start.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

def startVM(vmid):
    startTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).status.start.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

def revertLXC(vmid):
    revertTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).snapshot("initState").rollback.post(node=CONFIG.PROXMOX_NODE, vmid=vmid, snapname="initState")
    waitOnTask(revertTask)
    startTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).status.start.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

def revertVM(vmid):
    revertTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).snapshot("initState").rollback.post(node=CONFIG.PROXMOX_NODE, vmid=vmid, snapname="initState")
    waitOnTask(revertTask)
    startTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).status.start.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

def rebootLXC(vmid):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).status.current.get()
    if status["status"] == "running":
        restartTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).status.reboot.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
        waitOnTask(restartTask)
    else:
        startTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(vmid).status.start.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
        waitOnTask(startTask)
        
def rebootVM(vmid):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).status.current.get()
    if status["status"] == "running":
        restartTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).status.reboot.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
        waitOnTask(restartTask)
    else:
        startTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).status.start.post(node=CONFIG.PROXMOX_NODE, vmid=vmid)
        waitOnTask(startTask)

def shutdownLXC(delId):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(delId).status.stop.post(node=CONFIG.PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)

def shutdownVM(delId):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(delId).status.stop.post(node=CONFIG.PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)

def deleteLXC(delId):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(delId).status.stop.post(node=CONFIG.PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    deleteTask = proxmox.nodes(CONFIG.PROXMOX_NODE).lxc(delId).delete()
    waitOnTask(deleteTask)

def deleteVM(delId):
    status = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(delId).status.stop.post(node=CONFIG.PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    deleteTask = proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(delId).delete()
    waitOnTask(deleteTask)

def setupVNC(vmid):
    port = getNextVncPort()
    argsString = f"-vnc 0.0.0.0:{port},password=on"
    proxmox.nodes(CONFIG.PROXMOX_NODE).qemu(vmid).config.put(node=CONFIG.PROXMOX_NODE, vmid=vmid, args=argsString)

def setVNCPassword(vmid, password):
    command = urllib.parse.quote(f'set_password vnc {password} -d vnc2')
    proxmox(f"nodes/{CONFIG.PROXMOX_NODE}/qemu/{vmid}/monitor?command={command}").post() #Had to use alternative syntax due to bad string encoding in default syntax
