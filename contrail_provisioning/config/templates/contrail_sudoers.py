import string

template = string.Template("""
Defaults:contrail !requiretty

Cmnd_Alias CONFIGRESTART = /usr/sbin/service supervisor-config restart

contrail ALL = (root) NOPASSWD:CONFIGRESTART 
""")
