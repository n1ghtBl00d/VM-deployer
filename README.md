# Proxmox VM Deployer

Developed for [801Labs](801labs.org) to deploy Virtual Machines and Containers from Templates using the [Proxmox API](https://pve.proxmox.com/wiki/Proxmox_VE_API). Built with [Flask](flask.palletsprojects.com) and [Proxmoxer](https://github.com/proxmoxer/proxmoxer).

----

### Requirements:
* Python3
    * Flask
    * Flask-SocketIO
    * Proxmoxer
* arp-scan
* A user with admin permissions in Proxmox (I created bot@pve)
* Templates to clone from
    * Must have a description. The first line must be a MarkDown header with the name of the template (e.g. `# Test Template`)
* (Optional) A noVNC server for remote desktop access (I use [this docker container](https://hub.docker.com/r/geek1011/easy-novnc))
    * Add `[!ENABLE_VNC]` somewhere in the description to enable VNC access for a VM (Doesn't work for LXC containers)