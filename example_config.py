API_URL = "10.0.0.2"                    # Base URL/IP address of the proxmox server
API_USERNAME = "bot@pve"                # A user with admin permissions on the proxmox server. "___@pve" or "___@pam"
API_PASSWORD = "Super_secure_p@ssword"  # Password for above user
API_PORT = '8006'                       # The port of Proxmox's Web Ui and API endpoint   
SSL_VERIFY = False                      # Only set to true if SSL certificates are set up and up to date

PROXMOX_NODE = "proxmox"                # The name of your Proxmox Node

SSH_ENABLE = False                      # Set to True if you have passwordless ssh access set up to Proxmox. Speeds up aquisition of
                                        # IP Address of LXC Containers from a few seconds to basically instantaneous

VM_POOL = None                          # Leave as None unless you have configured a Pool and the associated permissions. If you have, put the name of the pool as a string

TEMPLATE_RANGE_LOWER = 200              # Range of VMIDs to be treated as templates to clone from
TEMPLATE_RANGE_UPPER = 299

CLONE_RANGE_LOWER = 300                 # Range of VMIDs to create new clones in
CLONE_RANGE_UPPER = 400