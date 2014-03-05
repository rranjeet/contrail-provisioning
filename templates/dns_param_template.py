import string

template = string.Template("""#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#
# DNS configuration options
#

[DEFAULT]
# dns_config_file=dns_config.xml
  hostip=$__contrail_host_ip__ # Resolved IP of `hostname`
  hostname=$__contrail_hostname__ # Retrieved as `hostname`
# http_server_port=8092
# log_category=
# log_disable=0
  log_file=/var/log/contrail/dns.log
# log_files_count=10
# log_file_size=10485760 # 10MB
# log_level=SYS_NOTICE
# log_local=0
# test_mode=0

[COLLECTOR]
# port=8086
# server= # Provided by discovery server

[DISCOVERY]
# port=5998
  server=$__contrail_discovery_ip__ # discovery-server IP address

[IFMAP]
  certs_store=$__contrail_cert_ops__
  password=$__contrail_ifmap_paswd__
# server_url= # Provided by discovery server, e.g. https://127.0.0.1:8443
  user=$__contrail_ifmap_usr__

""")
