import string

template = string.Template("""
#
# Vnswad configuration options
#

[CONTROL-NODE]
# IP address to be used to connect to control-node. Maximum of 2 IP addresses 
# (separated by a space) can be provided. If no IP is configured then the
# value provided by discovery service will be used. (Optional)
# server=10.0.0.1 10.0.0.2

[DEFAULT]
# Everything in this section is optional

# IP address and port to be used to connect to collector. If these are not
# configured, value provided by discovery service will be used. Multiple
# IP:port strings separated by space can be provided
# collectors=127.0.0.1:8086

# Enable/disable debug logging. Possible values are 0 (disable) and 1 (enable)
# debug=0

# Aging time for flow-records in seconds
# flow_cache_timeout=0

# Hostname of compute-node. If this is not configured value from `hostname`
# will be taken
# hostname=

# Http server port for inspecting vnswad state (useful for debugging)
# http_server_port=8085

# Category for logging. Default value is '*'
# log_category=

# Local log file name
# log_file=/var/log/contrail/vrouter.log

# Log severity levels. Possible values are SYS_EMERG, SYS_ALERT, SYS_CRIT, 
# SYS_ERR, SYS_WARN, SYS_NOTICE, SYS_INFO and SYS_DEBUG. Default is SYS_DEBUG
# log_level=SYS_DEBUG

# Enable/Disable local file logging. Possible values are 0 (disable) and 1 (enable)
# log_local=0

# Encapsulation type for tunnel. Possible values are MPLSoGRE, MPLSoUDP, VXLAN
# tunnel_type=

# Enable/Disable headless mode for agent. In headless mode agent retains last
# known good configuration from control node when all control nodes are lost.
# Possible values are true(enable) and false(disable)
# headless_mode=

[DISCOVERY]
# If COLLECTOR and/or CONTROL-NODE and/or DNS is not specified this section is 
# mandatory. Else this section is optional

# IP address of discovery server
server=$__contrail_discovery_ip__

# Number of control-nodes info to be provided by Discovery service. Possible
# values are 1 and 2
max_control_nodes=$__contrail_discovery_ncontrol__

[DNS]
# IP address and port to be used to connect to dns-node. Maximum of 2 IP
# addresses (separated by a space) can be provided. If no IP is configured then
# the value provided by discovery service will be used.
# server=10.0.0.1:53 10.0.0.2:53

[HYPERVISOR]
# Everything in this section is optional

# Hypervisor type. Possible values are kvm, xen and vmware
type=$__hypervisor_type__

# Link-local IP address and prefix in ip/prefix_len format (for xen)
# xen_ll_ip=

# Link-local interface name when hypervisor type is Xen
# xen_ll_interface=

# Physical interface name when hypervisor type is vmware
vmware_physical_interface=$__vmware_physical_interface__

[FLOWS]
# Everything in this section is optional

# Maximum flows allowed per VM (given as % of maximum system flows)
# max_vm_flows=100
# Maximum number of link-local flows allowed across all VMs
# max_system_linklocal_flows=4096
# Maximum number of link-local flows allowed per VM
# max_vm_linklocal_flows=1024

[METADATA]
# Shared secret for metadata proxy service (Optional)
# metadata_proxy_secret=contrail

[NETWORKS]
# control-channel IP address used by WEB-UI to connect to vnswad to fetch
# required information (Optional)
control_network_ip=$__contrail_control_ip__

[VIRTUAL-HOST-INTERFACE]
# Everything in this section is mandatory

# name of virtual host interface
name=vhost0

# IP address and prefix in ip/prefix_len format
ip=$__contrail_vhost_ip__

# Gateway IP address for virtual host
gateway=$__contrail_vhost_gateway__

# Physical interface name to which virtual host interface maps to
physical_interface=$__contrail_physical_intf__

# We can have multiple gateway sections with different indices in the 
# following format
# [GATEWAY-0]
# Name of the routing_instance for which the gateway is being configured
# routing_instance=default-domain:admin:public:public

# Gateway interface name
# interface=vgw

# Virtual network ip blocks for which gateway service is required. Each IP
# block is represented as ip/prefix. Multiple IP blocks are represented by 
# separating each with a space
# ip_blocks=1.1.1.1/24

# [GATEWAY-1]
# Name of the routing_instance for which the gateway is being configured
# routing_instance=default-domain:admin:public1:public1

# Gateway interface name
# interface=vgw1

# Virtual network ip blocks for which gateway service is required. Each IP
# block is represented as ip/prefix. Multiple IP blocks are represented by 
# separating each with a space
# ip_blocks=2.2.1.0/24 2.2.2.0/24

# Routes to be exported in routing_instance. Each route is represented as
# ip/prefix. Multiple routes are represented by separating each with a space
# routes=10.10.10.1/24 11.11.11.1/24
""")