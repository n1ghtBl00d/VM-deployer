#region imports
from api import *

import deployGroups
#endregion imports

#region global variables
currentGroups = []
#endregion global variables

def cloneGroup(group):
    groupId = len(currentGroups)
    currentGroups.append({
        "groupId": groupId,
        "createdFrom": group["groupName"],
        "vmidMap": [],
        "ipAddresses": []

    })
    threads = []
    for vmid in group["vmids"]:
        createThread = threading.Thread(target=groupCreateAndStart, args=[vmid, groupId])
        createThread.start()
        threads.append(createThread)
        statusThread = threading.Timer(5, groupGetIP, args=[vmid, groupId])
        statusThread.start()
        threads.append(statusThread)
    for mapping in group["firewallConnections"]:
        enableFirewall(mapping["vmid"])
    for thread in threads:
        thread.join()
    for rule in group["firewallConnections"]:
        for listing in currentGroups[groupId]["ipAddresses"]:
            if (listing[0] == rule["fromId"]):
                fromIP = listing[1]
                break
        addFirewallAllowedIP(rule["vmid"], fromIP, rule["interface"])

def groupGetIP(vmid, groupId):
    ipAddr = getIP(vmid)
    if (ipAddr == "N/A"):
        #Wait and retry once
        time.sleep(20)
        ipAddr = getIP(vmid)
    currentGroups[groupId]["ipAddresses"].append((vmid, ipAddr))

def groupCreateAndStart(vmid, groupId):
    cloneid = getNextId()
    name = f"Group{groupId}-" + getName(vmid)
    newid = create(vmid, cloneid, name=name)
    start(newid)
    currentGroups[groupId]["vmidMap"].append((vmid, newid))
    
    
