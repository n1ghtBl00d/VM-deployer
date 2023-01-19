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
* Two templates set up on Proxmox - 1 LXC and 1 VM
* Key-based SSH access to the Proxmox server (**optional** - speeds up discovery of IP addresses of LXC containers)