import string

template = string.Template("""
#!/bin/sh

# chkconfig: 2345 99 01
# description: Juniper Network Virtualization API

$__contrail_supervisorctl_lines__

#if os.path.exists('/tmp/supervisord_config.sock'):
#    supervisorctl -s unix:///tmp/supervisord_config.sock ${1} `basename ${0}`
#else:
#    supervisorctl -s unix:///var/run/supervisord_config.sock ${1} `basename ${0}`
""")
