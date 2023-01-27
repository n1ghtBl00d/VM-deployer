API_URL = "10.0.0.2"                    # Base URL/IP address of the proxmox server
API_USERNAME = "bot@pve"                # A user with admin permissions on the proxmox server. "___@pve" or "___@pam"
API_PASSWORD = "Super_secure_p@ssword"  # Password for above user
API_PORT = '8006'                       # The port of Proxmox's Web Ui and API endpoint   
SSL_VERIFY = 'false'                    # Only set to true if SSL certificates are set up and up to date

PROXMOX_NODE = "proxmox"                # The name of your Proxmox Node

SSH_ENABLE = False                      # Set to True if you have passwordless ssh access set up to Proxmox. Speeds up aquisition of
                                        # IP Address of LXC Containers from a few seconds to basically instantaneous

VM_TEMPLATE_ID = 198                    # Proxmox ID of the template VM to be cloned
LXC_TEMPLATE_ID = 199                   # Proxmox ID of the template LXC to be cloned