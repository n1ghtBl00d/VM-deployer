#region imports
from api import *

import deployGroups
#endregion imports

#region global variables
currentGroups = []
#endregion global variables

def api_groups_init(socket):
    global socketio 
    socketio = socket

def cloneGroup(group):
    groupId = len(currentGroups)
    socketio.emit("statusUpdateGroup", {"status": f"Cloning group {group['groupName']} to {groupId}", "groupID": groupId})
    currentGroups.append({
        "groupId": groupId,
        "createdFrom": group["groupName"],
        "vmidMap": [],
        "ipAddresses": []

    })
    print("Creating VMs")
    createThreads = []
    for vmid in group["vmids"]:
        createThread = threading.Thread(target=groupCreateAndStart, args=[vmid, groupId])
        createThread.start()
        createThreads.append(createThread)
    for thread in createThreads:
        thread.join()
    print("Done Creating")
    socketio.emit("statusUpdateGroup", {"status": f"All VMs created. Getting status", "groupID": groupId})
    print("Firewall enable")
    for mapping in group["firewallConnections"]:
        enableFirewall(mapping["vmid"])
    print("Getting Status")
    statusThreads = []
    for entry in currentGroups[groupId]["vmidMap"]:
        vmid = entry[1]
        statusThread = threading.Thread(target=groupGetStatus, args=[vmid, groupId])
        statusThread.start()
        statusThreads.append(statusThread)
    for thread in statusThreads:
        thread.join()
    print("Got all statuses")
    print(f"Creating Firewall rules for group {groupId}")
    print(group)
    fromIP = ""
    for rule in group["firewallConnections"]:
        for listing in currentGroups[groupId]["ipAddresses"]:
            for entry in currentGroups[groupId]["vmidMap"]:
                print(f"entry[1]({entry[1]} == listing[0]({listing[0]}), rule[fromid]({rule['fromId']}) == entry[0]({entry[0]})")
                if(entry[1] == listing[0]):
                    if (rule["fromId"] == entry[0]):
                        fromIP = listing[1]
                        break
        addFirewallAllowedIP(rule["vmid"], fromIP, rule["interface"])

def groupGetStatus(vmid, groupId):
    statusEntry = updateStatus(vmid)
    currentGroups[groupId]["ipAddresses"].append((vmid, statusEntry["ipAddr"]))
    socketio.emit("vmListEntry", {"vmid": statusEntry["vmid"], "name": statusEntry["name"], "status": statusEntry["status"], "ip": statusEntry["ipAddr"], "vncStatus": statusEntry["vncStatus"]})


def groupCreateAndStart(vmid, groupId):
    cloneid = getNextId()
    print(f"Entered groupCreateAndStart({vmid}, {groupId}) - creating new: {cloneid}")
    name = f"Group{groupId}-" + getName(vmid)
    newid = create(vmid, cloneid, name=name)
    start(newid)
    currentGroups[groupId]["vmidMap"].append((vmid, newid))
    print(f"Created {newid}")
    socketio.emit("statusUpdate", {"status": f"Created VM as part of group {groupId}", "newID": newid})
    
    
