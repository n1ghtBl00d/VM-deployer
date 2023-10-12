Groups = [
    {
    "groupName":   "Example 1",
    "vmids":        [200, 201],
    "firewallConnections": []
    },
    {
    "groupName":   "Example 2",
    "vmids":        [202, 203],
    "firewallConnections": [
        {
            "vmid": 203,
            "interface": "net0",
            "fromId": 202          
        },
        {
            "vmid": 202,
            "interface": "net1",
            "fromId": 203
        }
    ]
    }
]