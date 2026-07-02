"""Node/relationship vocabulary for `navixa_graph`, matching the Data
Normalization model (Section 11) and Graph Engine design (Section 12).
"""

RESOURCE_TYPE_TO_LABEL: dict[str, str] = {
    "network": "Network",
    "subnet": "Subnet",
    "route_table": "RouteTable",
    "route": "Route",
    "gateway": "Gateway",
    "firewall": "Firewall",
    "security_group": "SecurityGroup",
    "network_interface": "NetworkInterface",
    "load_balancer": "LoadBalancer",
    "endpoint": "Endpoint",
    "compute_instance": "ComputeInstance",
    "peering_connection": "PeeringConnection",
    "public_ip": "PublicIP",
}

REL_PART_OF = "PART_OF"
REL_PEERED_WITH = "PEERED_WITH"
REL_IN_SCOPE = "IN_SCOPE"
REL_DESIGNATED_HUB = "DESIGNATED_HUB"
