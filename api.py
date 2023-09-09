#region imports
from proxmoxer import ProxmoxAPI, core
import threading, os, time, subprocess, re, urllib.parse, datetime, requests
from ratelimit import limits, sleep_and_retry, RateLimitException
import backoff

# import .config as CONFIG 
from .config import *
print(API_PASSWORD)
#endregion imports

#region global variables
arpResult = {
    "results": [],
    "updateTime": datetime.datetime(1970, 1, 1)
}

ipPattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
macPattern = re.compile(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
vncPattern = re.compile(r':\s*(\d*)')

print(API_PORT)
proxmox = ProxmoxAPI(
    API_URL, user=API_USERNAME, password=API_PASSWORD, verify_ssl=SSL_VERIFY, port=API_PORT
)
for node in proxmox.nodes.get():
    for vm in proxmox.nodes(node["node"]).qemu.get():
        print(f"{vm['vmid']}. {vm['name']} => {vm['status']}")
#endregion global variables

#region utilities
def heartBeat():
    proxmox.nodes.get()
    print("heartbeat")
    heartBeatThread = threading.Timer(3600, heartBeat)
    heartBeatThread.start()

def waitOnTask(task_id):
    data = {"status": ""}
    while (data["status"] != "stopped"):
        data = proxmox.nodes(PROXMOX_NODE).tasks(task_id).status.get()

def clean_string(string):
    cleaned = []
    for char in string:
        if char.isalnum():
            cleaned.append(char)
        elif char.isspace():
            cleaned.append("-")
        elif (char == '.'):
            cleaned.append(char)
        elif (char == '-'):
            cleaned.append(char)
    return "".join(cleaned)

#region updateStatus()
def updateStatus(vmid):
    hostType = getType(vmid)
    if (hostType == "lxc"):
        return updateStatusLXC(vmid)
    if (hostType == "vm"):
        return updateStatusVM(vmid)
    
def updateStatusLXC(lxc):
    status = proxmox.nodes(PROXMOX_NODE).lxc(lxc).status.current.get()
    if status["status"] == "running":
        ipAddr = getIP(lxc)
    else:
        ipAddr = "n/a"
    statusEntry = {
        "vmid": lxc,
        "name": status["name"],
        "status": status["status"],
        "ipAddr": ipAddr,
        "vncStatus": False
    }
    return statusEntry

def updateStatusVM(vm):
    status = proxmox.nodes(PROXMOX_NODE).qemu(vm).status.current.get()
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
        "vncStatus": vncEnabled
    }
    return statusEntry
#endregion updateStatus()

#endregion utilites

#region get info
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

def getType(vmid):
    lxcs = getLXCs() + getTemplateLXCs()
    vms = getVMs() + getTemplateVMs()

    if vmid in lxcs:
        return "lxc"
    if vmid in vms:
        return "vm"
    else:
        return "error"

def getVNCports():
    ports = []
    for vm in proxmox.nodes(PROXMOX_NODE).qemu.get():
        vmid = int(vm["vmid"])
        config = proxmox.nodes(PROXMOX_NODE).qemu(vmid).config().get() #Get ports from all vms, not just clones
        if("args" in keys()):
            args = config["args"]
            port = str(vncPattern.search(args)[1])
            ports.append({"vmid": vmid, "port": int(port)})
    return ports

def checkTemplateVNC(templateId):
    config = proxmox.nodes(PROXMOX_NODE).qemu(templateId).config().get()
    description = config["description"]
    if "[!ENABLE_VNC]" in description:
        return True
    else:
        return False

def getName(vmid):
    hostType = getType(vmid)
    if hostType == "lxc":
        config = proxmox.nodes(PROXMOX_NODE).lxc(vmid).config().get()
        description = config["description"]
        name = description.partition('\n')[0][2:]
        return name
    if hostType == "vm":
        config = proxmox.nodes(PROXMOX_NODE).qemu(vmid).config().get()
        description = config["description"]
        name = description.partition('\n')[0][2:]
        return name
    #If Error:
    return "Name Not Found"

def getUserMachines(username):
    lxcs = proxmox.nodes(PROXMOX_NODE).lxc.get()
    vms  = proxmox.nodes(PROXMOX_NODE).qemu.get()
    machines = lxcs + vms 
    userMachines = []

    for machine in machines:
        if machine.get('tags') == username:
            userMachines.append(machine)

    return userMachines

def getMachineExists(username, vmid):
    name = clean_string(getName(vmid))
    userMachine = {}
    machines = getUserMachines(username)
    
    for machine in machines:
        if machine.get('name') == name:
            userMachine = machine
            break

    if userMachine:
        if userMachine['status'] == 'stopped':
            print('STARTING', userMachine)
            startTask = proxmox(f"nodes/{PROXMOX_NODE}/{userMachine['type']}/{userMachine['vmid']}/status/start").post()
            waitOnTask(startTask)
        return {
            'ip': getIP(int(userMachine['vmid'])),
            'name': userMachine.get('name', 'N/A'),
            'status': userMachine['status']
        }
    return {}

def getNameLXC(vmid):
    config = proxmox.nodes(PROXMOX_NODE).lxc(vmid).config().get()
    description = config["description"]
    name = description.partition('\n')[0][2:]
    return name

def getNameVM(vmid):
    config = proxmox.nodes(PROXMOX_NODE).qemu(vmid).config().get()
    description = config["description"]
    name = description.partition('\n')[0][2:]
    return name

def getAllTemplates():
    templates = [] 
    lxcs = getTemplateLXCs()
    vms = getTemplateVMs()
    for lxc in lxcs:
        templates.append({"vmid": lxc, "name": getName(lxc)})
    for vm in vms:
        templates.append({"vmid": vm, "name": getName(vm)})
    return templates


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

def getNextVncPort():
    ports = getVNCports()
    if(ports == []):
        return 1
    else:
        for x in range(1, 99):
            if not any((p["port"]) == x for p in ports):
                return x
#endregion get info

#region Networking
def getIP(vmid):
    hostType = getType(vmid)
    if hostType == "lxc":
        config = proxmox.nodes(PROXMOX_NODE).lxc(vmid).config().get()
        mac = str(macPattern.search(str(config))[0])
        return findIPbyMAC(mac)
    if hostType == "vm":
        config = proxmox.nodes(PROXMOX_NODE).qemu(vmid).config().get()
        mac = str(macPattern.search(str(config))[0])
        return findIPbyMAC(mac)
    return "N/A"

def findIPbyMAC(mac):
    mac = mac.lower()
    now = datetime.datetime.now()
    if (arpResult["updateTime"] < now-datetime.timedelta(seconds=60)):
        arpScan()
    for result in arpResult["results"]:
        if result[1] == mac:
            return result[0]
    
    #If not found, try again but force arp scan
    arpScan()
    for result in arpResult["results"]:
        if result[1] == mac:
            return result[0]
    
    #If not found
    return "Not Found"

def arpScan():
    resultString = ""
    resultsArr = []
    for network in NETWORKS:
        try:
            resultString += str(subprocess.check_output(f"arp-scan -I {network['interface']} {network['address']}", shell=True).decode('utf-8')).lower()
        except Exception as e:
            pass
    results = resultString.split("\n")
    for result in results:
        if(ipPattern.search(result)):
            values = result.split("\t")
            resultsArr.append((values[0], values[1]))
    arpResult["results"] = resultsArr
    arpResult["updateTime"] = datetime.datetime.now()


#region firewall
def enableFirewall(vmid):
    hostType = getType(vmid)
    if hostType == "lxc":
        firewallTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).firewall.options.put(node=PROXMOX_NODE, vmid=vmid, enable=1)
    if hostType == "vm":
        firewallTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).firewall.options.put(node=PROXMOX_NODE, vmid=vmid, enable=1)

def addFirewallAllowedIP(vmid, ipAddr, interface="net0"):
    hostType = getType(vmid)
    if hostType == "lxc":
        proxmox.nodes(PROXMOX_NODE).lxc(vmid).firewall.rules.post(node=PROXMOX_NODE, vmid=vmid, enable=1, type="in", action="ACCEPT", log="nolog", source=ipAddr, iface=interface)
    if hostType == "vm":
        proxmox.nodes(PROXMOX_NODE).qemu(vmid).firewall.rules.post(node=PROXMOX_NODE, vmid=vmid, enable=1, type="in", action="ACCEPT", log="nolog", source=ipAddr, iface=interface)
#endregion firewall


#endregion Netowrking

#region basic VM functions

#region Create()
def create(cloneid, newid, username, name="default", vnc=None):
    hostType = getType(cloneid)
    if (hostType == "lxc"):
        return createLXC(cloneid, newid, username, name)
    if (hostType == "vm"):
        return createVM(cloneid, newid, username, name, vnc)
    

@backoff.on_exception(backoff.constant, requests.exceptions.ReadTimeout, interval=10, max_tries = 5)
@sleep_and_retry
@limits(calls=1, period=30) #Max 1 call per 30 seconds
def createLXC(cloneid, newId, username, name="default"):
    if(name == "default"):
        name = getNameLXC(cloneid)
    name = clean_string(name.strip())
    try:
        cloneTask = proxmox.nodes(PROXMOX_NODE).lxc(cloneid).clone.post(newid=newId, node=PROXMOX_NODE, vmid=cloneid, pool=VM_POOL, hostname=name)
        waitOnTask(cloneTask)
        snapshotTask = proxmox.nodes(PROXMOX_NODE).lxc(newId).snapshot.post(vmid=newId, node=PROXMOX_NODE, snapname="initState")
        waitOnTask(snapshotTask)
        proxmox.nodes(PROXMOX_NODE).lxc(newId).config().put(tags=username)
        return newId
    except core.ResourceException:
        return createLXC(cloneid, getNextId(), username, name)

@backoff.on_exception(backoff.expo, (requests.exceptions.ReadTimeout, requests.exceptions.ReadTimeout), max_tries = 5)
@sleep_and_retry
@limits(calls=1, period=30) #Max 1 call per 30 seconds
def createVM(cloneid, newId, username, name="default", vnc=None):
    if(name == "default"):
        name = getNameVM(cloneid)
    name = clean_string(name.strip())
    if(vnc == None):
        vnc = checkTemplateVNC(cloneid)
    try:
        cloneTask = proxmox.nodes(PROXMOX_NODE).qemu(cloneid).clone.post(newid=newId, node=PROXMOX_NODE, vmid=cloneid, pool=VM_POOL, name=name)
        waitOnTask(cloneTask)
        if(vnc == True):
            setupVNC(newId)
        snapshotTask = proxmox.nodes(PROXMOX_NODE).qemu(newId).snapshot.post(vmid=newId, node=PROXMOX_NODE, snapname="initState")
        waitOnTask(snapshotTask)
        setTagTask = proxmox.nodes(PROXMOX_NODE).qemu(newId).config(tags=username).put()
        waitOnTask(setTagTask)
        return newId
    except core.ResourceException:
        return createVM(cloneid, getNextId(), username, name, vnc)
    
#endregion create()

#region start()    
def start(vmid):
    hostType = getType(vmid)
    if (hostType == "lxc"):
        startLXC(vmid)
    if (hostType == "vm"):
        startVM(vmid)

def startLXC(vmid):
    startTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

def startVM(vmid):
    startTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

#endregion start()

#region revert()
def revert(vmid):
    hostType = getType(vmid)
    if (hostType == "lxc"):
        revertLXC(vmid)
    if (hostType == "vm"):
        revertVM(vmid)

def revertLXC(vmid):
    revertTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).snapshot("initState").rollback.post(node=PROXMOX_NODE, vmid=vmid, snapname="initState")
    waitOnTask(revertTask)
    startTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)

def revertVM(vmid):
    revertTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).snapshot("initState").rollback.post(node=PROXMOX_NODE, vmid=vmid, snapname="initState")
    waitOnTask(revertTask)
    startTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
    waitOnTask(startTask)
#endregion revert()

#region reboot()
def reboot(vmid):
    hostType = getType(vmid)
    if (hostType == "lxc"):
        rebootLXC(vmid)
    if (hostType == "vm"):
        rebootVM(vmid)

def rebootLXC(vmid):
    status = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.current.get()
    if status["status"] == "running":
        restartTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.reboot.post(node=PROXMOX_NODE, vmid=vmid)
        waitOnTask(restartTask)
    else:
        startTask = proxmox.nodes(PROXMOX_NODE).lxc(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
        waitOnTask(startTask)
        
def rebootVM(vmid):
    status = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.current.get()
    if status["status"] == "running":
        restartTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.reboot.post(node=PROXMOX_NODE, vmid=vmid)
        waitOnTask(restartTask)
    else:
        startTask = proxmox.nodes(PROXMOX_NODE).qemu(vmid).status.start.post(node=PROXMOX_NODE, vmid=vmid)
        waitOnTask(startTask)
#endregion reboot()

#region shutdown()
def shutdown(delId):
    hostType = getType(delId)
    if (hostType == "lxc"):
        shutdownLXC(delId)
    if (hostType == "vm"):
        shutdownVM(delId)

def shutdownLXC(delId):
    status = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)

def shutdownVM(delId):
    status = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
#endregion shutdown()

#region delete()
def delete(delId):
    hostType = getType(delId)
    if (hostType == "lxc"):
        deleteLXC(delId)
    if (hostType == "vm"):
        deleteVM(delId)

def deleteLXC(delId):
    status = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(PROXMOX_NODE).lxc(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    deleteTask = proxmox.nodes(PROXMOX_NODE).lxc(delId).delete()
    waitOnTask(deleteTask)

def deleteVM(delId):
    status = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.current.get()
    if(status["status"] != "stopped"):
        shutdownTask = proxmox.nodes(PROXMOX_NODE).qemu(delId).status.stop.post(node=PROXMOX_NODE, vmid=delId)
        waitOnTask(shutdownTask)
    deleteTask = proxmox.nodes(PROXMOX_NODE).qemu(delId).delete()
    waitOnTask(deleteTask)
#endregion delete()

#endregion basic VM functions

#region vnc
def setupVNC(vmid):
    port = getNextVncPort()
    argsString = f"-vnc 0.0.0.0:{port},password=on"
    proxmox.nodes(PROXMOX_NODE).qemu(vmid).put(node=PROXMOX_NODE, vmid=vmid, args=argsString)

def setVNCPassword(vmid, password):
    command = urllib.parse.quote(f'set_password vnc {password} -d vnc2')
    proxmox(f"nodes/{PROXMOX_NODE}/qemu/{vmid}/monitor?command={command}").post() #Had to use alternative syntax due to bad string encoding in default syntax
#endregion vnc