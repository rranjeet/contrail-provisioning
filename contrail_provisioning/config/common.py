#!/usr/bin/python
#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#
"""Provision's Contrail Config components."""

import os
from time import sleep

from fabric.api import local
from fabric.context_managers import settings

from contrail_provisioning.common.base import ContrailSetup
from contrail_provisioning.database.base import DatabaseCommon
from contrail_provisioning.config.templates import contrail_api_conf
from contrail_provisioning.config.templates import contrail_api_ini
from contrail_provisioning.config.templates import contrail_api_ini_centos
from contrail_provisioning.config.templates import contrail_api_svc
from contrail_provisioning.config.templates import contrail_schema_transformer_conf
from contrail_provisioning.config.templates import contrail_device_manager_conf
from contrail_provisioning.config.templates import contrail_svc_monitor_conf
from contrail_provisioning.config.templates import contrail_sudoers
from contrail_provisioning.config.templates import contrail_config_nodemgr_template
from contrail_provisioning.common.templates import contrail_database_template
from contrail_provisioning.config.templates import contrail_device_manager_ini

class ConfigBaseSetup(ContrailSetup):
    def __init__(self, config_args, args_str=None):
        super(ConfigBaseSetup, self).__init__()
        self._args = config_args

        self.cfgm_ip = self._args.self_ip
        self.cassandra_server_list = [(cassandra_server_ip, '9160')\
            for cassandra_server_ip in self._args.cassandra_ip_list]
        self.zk_servers = ','.join(self._args.zookeeper_ip_list)
        self.zk_servers_ports = ','.join(['%s:2181' %(s)\
            for s in self._args.zookeeper_ip_list])

        self.control_node_users = '\n'.join(['%s:%s' %(s, s)\
            for s in self._args.control_ip_list])
        self.control_node_dns_users = '\n'.join(['%s.dns:%s.dns' %(s, s)\
            for s in self._args.control_ip_list])
        amqp_ip_list = [self.cfgm_ip]
        if self._args.amqp_ip_list:
            amqp_ip_list = self._args.amqp_ip_list
        self.rabbit_servers = ','.join(['%s:%s' % (amqp, self._args.amqp_port)\
                                        for amqp in amqp_ip_list])
        self.amqp_password = self._args.amqp_password or ''
        self.contrail_internal_vip = (self._args.contrail_internal_vip or
                                 self._args.internal_vip)
        self.api_ssl_enabled = False
        if (self._args.apiserver_keyfile and
                self._args.apiserver_certfile and self._args.apiserver_cafile):
            self.api_ssl_enabled = True
        self.keystone_ssl_enabled = False

    def fixup_config_files(self):
        self.fixup_cassandra_config()
        self.fixup_contrail_api_config_file()
        if self.pdist in ['Ubuntu'] and self.pdistversion == '16.04':
            pass
        else:
            self.fixup_contrail_api_supervisor_ini()
            self.fixup_contrail_api_initd()
            self.fixup_device_manager_ini()
        self.fixup_schema_transformer_config_file()
        self.fixup_device_manager_config_file()
        self.fixup_svc_monitor_config_file()
        self.fixup_vnc_api_lib_ini()
        self.fixup_contrail_sudoers()
        self.fixup_contrail_config_nodemgr()
        self.fixup_cassandra_config()
        if self._args.use_certs:
            local("sudo setup-pki.sh /etc/contrail/ssl")


    def fixup_contrail_api_config_file(self):
        if self._args.orchestrator == 'vcenter':
            aaa_mode = "no-auth"
        else:
            aaa_mode = self._args.aaa_mode
        if self.pdist in ['Ubuntu'] and self.pdistversion == '16.04':
            listen_port = 9100
        else:
            listen_port = 8082
  
        # contrail-api.conf
        template_vals = {'__contrail_listen_ip_addr__': '0.0.0.0',
                         '__contrail_listen_port__': listen_port,
                         '__contrail_use_certs__': self._args.use_certs,
                         '__rabbit_server_ip__': self.rabbit_servers,
                         '__contrail_log_file__': '/var/log/contrail/contrail-api.log',
                         '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in self.cassandra_server_list),
                         '__contrail_zookeeper_server_ip__': self.zk_servers_ports,
                         '__contrail_cloud_admin_role__': "cloud_admin_role=%s" % self._args.cloud_admin_role if self._args.cloud_admin_role else '',
                         '__contrail_aaa_mode__': "aaa_mode=%s" % aaa_mode if aaa_mode else '',
                         '__contrail_collectors__': \
                             ' '.join('%s:%s' %(server, '8086') for server \
                                in self._args.collector_ip_list)
                        }
        self._template_substitute_write(contrail_api_conf.template,
                                        template_vals, self._temp_dir_name + '/contrail-api.conf')
        local("sudo mv %s/contrail-api.conf /etc/contrail/" %(self._temp_dir_name))
        if self.amqp_password:
            local("sudo openstack-config --set /etc/contrail/contrail-api.conf DEFAULTS rabbit_password %s" % self.amqp_password)

    def fixup_contrail_api_supervisor_ini(self, config_files=['/etc/contrail/contrail-api.conf', '/etc/contrail/contrail-database.conf']):
        # supervisor contrail-api.ini
        config_file_args = ' --conf_file '.join(config_files)
        template_vals = {'__contrail_api_port_base__': '910', # 910x
                         '__contrail_api_nworkers__': self._args.nworkers,
                         '__contrail_config_file_args__' : config_file_args,
                        }
        if self.pdist == 'Ubuntu':
            tmpl = contrail_api_ini.template
        else:
            tmpl = contrail_api_ini_centos.template

        self._template_substitute_write(tmpl,
                                        template_vals, self._temp_dir_name + '/contrail-api.ini')
        local("sudo mv %s/contrail-api.ini /etc/contrail/supervisord_config_files/" %(self._temp_dir_name))

    def fixup_contrail_api_initd(self):
        # initd script wrapper for contrail-api
            sctl_lines = ''
            for worker_id in range(int(self._args.nworkers)):
                sctl_line = 'if [ -e /tmp/supervisord_config.sock ]; then\n'
                sctl_line += '    supervisorctl -s unix:///tmp/supervisord_config.sock ' + \
                            '${1} `basename ${0}:%s`\n' %(worker_id)
                sctl_line += 'else\n'
                sctl_line += '    supervisorctl -s unix:///var/run/supervisord_config.sock ' + \
                            '${1} `basename ${0}:%s`\n' %(worker_id)
                sctl_line += 'fi\n'
                sctl_lines = sctl_lines + sctl_line

            template_vals = {'__contrail_supervisorctl_lines__': sctl_lines,
                            }
            self._template_substitute_write(contrail_api_svc.template,
                                            template_vals, self._temp_dir_name + '/contrail-api')
            local("sudo mv %s/contrail-api /etc/init.d/" %(self._temp_dir_name))
            local("sudo chmod a+x /etc/init.d/contrail-api")

    def fixup_schema_transformer_config_file(self):
        # contrail-schema.conf
        template_vals = {'__contrail_api_server_ip__': self.contrail_internal_vip or self.cfgm_ip,
                         '__contrail_api_server_port__': '8082',
                         '__api_server_use_ssl__': 'True' if self.api_ssl_enabled else 'False',
                         '__contrail_zookeeper_server_ip__': self.zk_servers_ports,
                         '__contrail_use_certs__': self._args.use_certs,
                         '__contrail_keyfile_location__': '/etc/contrail/ssl/private_keys/schema_xfer_key.pem',
                         '__contrail_certfile_location__': '/etc/contrail/ssl/certs/schema_xfer.pem',
                         '__contrail_cacertfile_location__': '/etc/contrail/ssl/certs/ca.pem',
                         '__contrail_log_file__' : '/var/log/contrail/contrail-schema.log',
                         '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in self.cassandra_server_list),
                         '__rabbit_server_ip__': self.rabbit_servers,
                         '__contrail_collectors__': \
                             ' '.join('%s:%s' %(server, '8086') for server \
                                in self._args.collector_ip_list)
                        }
        self._template_substitute_write(contrail_schema_transformer_conf.template,
                                        template_vals, self._temp_dir_name + '/contrail-schema.conf')
        local("sudo mv %s/contrail-schema.conf /etc/contrail/contrail-schema.conf" %(self._temp_dir_name))
        if os.path.exists('/etc/init.d/contrail-schema'):
            local("sudo chmod a+x /etc/init.d/contrail-schema")
        if self.amqp_password:
            local("sudo openstack-config --set /etc/contrail/contrail-schema.conf DEFAULTS rabbit_password %s" % self.amqp_password)

    def fixup_device_manager_ini(self,config_files=
                                      ['/etc/contrail/contrail-device-manager.conf',
                                       '/etc/contrail/contrail-keystone-auth.conf']
                                ):
        # If cassandra user name provided add the cassandra_database.conf file
        # to the ini
        if self._args.cassandra_user is not None:
            config_files.append('/etc/contrail/contrail-database.conf')
        config_file_args = ' --conf_file '.join(config_files)
        template_vals = {'__contrail_config_file_args__': config_file_args}
        self._template_substitute_write(contrail_device_manager_ini.template,
                                        template_vals, self._temp_dir_name + '/contrail-device-manager.ini')
        local("sudo mv %s/contrail-device-manager.ini /etc/contrail/supervisord_config_files/" %(self._temp_dir_name))

    def fixup_device_manager_config_file(self):
        # contrail-device-manager.conf
        template_vals = {'__rabbit_server_ip__': self.rabbit_servers,
                         '__contrail_api_server_ip__': self.contrail_internal_vip or self.cfgm_ip,
                         '__contrail_api_server_port__': '8082',
                         '__api_server_use_ssl__': 'True' if self.api_ssl_enabled else 'False',
                         '__contrail_zookeeper_server_ip__': self.zk_servers_ports,
                         '__contrail_log_file__' : '/var/log/contrail/contrail-device-manager.log',
                         '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in self.cassandra_server_list),
                         '__contrail_collectors__': \
                             ' '.join('%s:%s' %(server, '8086') for server \
                                in self._args.collector_ip_list) 
                        }
        self._template_substitute_write(contrail_device_manager_conf.template,
                                        template_vals, self._temp_dir_name + '/contrail-device-manager.conf')
        local("sudo mv %s/contrail-device-manager.conf /etc/contrail/contrail-device-manager.conf" %(self._temp_dir_name))
        #local("sudo chmod a+x /etc/init.d/contrail-device-manager")
        if self.amqp_password:
            local("sudo openstack-config --set /etc/contrail/contrail-device-manager.conf DEFAULTS rabbit_password %s" % self.amqp_password)

    def fixup_svc_monitor_config_file(self):
        # contrail-svc-monitor.conf
        template_vals = {'__rabbit_server_ip__': self.rabbit_servers,
                         '__contrail_api_server_ip__': self.contrail_internal_vip or self.cfgm_ip,
                         '__contrail_api_server_port__': '8082',
                         '__api_server_use_ssl__': 'True' if self.api_ssl_enabled else 'False',
                         '__contrail_zookeeper_server_ip__': self.zk_servers_ports,
                         '__contrail_use_certs__': self._args.use_certs,
                         '__contrail_keyfile_location__': '/etc/contrail/ssl/private_keys/svc_monitor_key.pem',
                         '__contrail_certfile_location__': '/etc/contrail/ssl/certs/svc_monitor.pem',
                         '__contrail_cacertfile_location__': '/etc/contrail/ssl/certs/ca.pem',
                         '__contrail_log_file__' : '/var/log/contrail/contrail-svc-monitor.log',
                         '__contrail_cassandra_server_list__' : ' '.join('%s:%s' % cassandra_server for cassandra_server in self.cassandra_server_list),
                         '__contrail_region_name__': self._args.region_name,
                         '__contrail_collectors__': \
                             ' '.join('%s:%s' %(server, '8086') for server \
                                in self._args.collector_ip_list),
                         '__contrail_analytics_server_list__': \
                             ' '.join('%s:%s' %(server, '8081') for server \
                                in self._args.collector_ip_list)
                        }
        self._template_substitute_write(contrail_svc_monitor_conf.template,
                                        template_vals, self._temp_dir_name + '/contrail-svc-monitor.conf')
        local("sudo mv %s/contrail-svc-monitor.conf /etc/contrail/contrail-svc-monitor.conf" %(self._temp_dir_name))
        if self.amqp_password:
            local("sudo openstack-config --set /etc/contrail/contrail-svc-monitor.conf DEFAULTS rabbit_password %s" % self.amqp_password)

    def fixup_contrail_sudoers(self):
        # sudoers for contrail
            template_vals = {
                            }
            self._template_substitute_write(contrail_sudoers.template,
                                            template_vals, self._temp_dir_name + '/contrail_sudoers')
            local("sudo mv %s/contrail_sudoers /etc/sudoers.d/" %(self._temp_dir_name))
            local("sudo chmod 440 /etc/sudoers.d/contrail_sudoers")

    def fixup_contrail_config_nodemgr(self):
        template_vals = {
                         '__contrail_collectors__': \
                             ' '.join('%s:%s' %(server, '8086') for server \
                                in self._args.collector_ip_list) 
                        }
        self._template_substitute_write(contrail_config_nodemgr_template.template,
                                        template_vals, self._temp_dir_name + '/contrail-config-nodemgr.conf')
        local("sudo mv %s/contrail-config-nodemgr.conf /etc/contrail/contrail-config-nodemgr.conf" %(self._temp_dir_name))

    def fixup_cassandra_config(self):
        if self._args.cassandra_user is not None:
            if os.path.isfile('/etc/contrail/contrail-database.conf') is not True:
                 # Create conf file
                 template_vals = {'__cassandra_user__': self._args.cassandra_user,
                                  '__cassandra_password__': self._args.cassandra_password
                                 }
                 self._template_substitute_write(contrail_database_template.template,
                                        template_vals, self._temp_dir_name + '/contrail-config-database.conf')
                 local("sudo mv %s/contrail-config-database.conf /etc/contrail/contrail-database.conf" %(self._temp_dir_name))
 
    def restart_config(self):
        local('sudo service supervisor-config restart')

    def run_services(self):
        local("sudo config-server-setup.sh")
        # Wait for supervisor to start contrail-api and rabbitmq
        for i in range(10):
            services_status = {'contrail-api' : 'down', 'rabbitmq-server' : 'down'}
            for service in services_status.keys():
                with settings(warn_only=True):
                    status = local("sudo service %s status" % service, capture=True)
                if status.succeeded and 'running' in status.lower():
                    print "[%s] started by supervisor config." % service
                    services_status[service] = 'running'
                else:
                    print "Error %s in getting status of [%s]." \
                           %(status.__dict__, service)
                    services_status[service] = 'down'

            if 'down' in services_status.values():
                print "[contrail-api and rabbitmq] not yet started by supervisor config, Retrying."
                sleep(2)
            else:
                print "[contrail-api and rabbitmq] started by supervisor config, continue to provision."
                return

    def setup_database(self):
        db = DatabaseCommon()
        db.fixup_zookeeper_configs(self._args.zookeeper_ip_list,
                                   self._args.cfgm_index)
        db_services = ['zookeeper']
        if self._args.manage_db:
            db.create_data_dir(self._args.data_dir)
            db.fixup_etc_hosts_file(self._args.self_ip, self.hostname)
            db.fixup_cassandra_config_file(self._args.self_ip,
                                           self._args.seed_list,
                                           self._args.data_dir,
                                           self._args.ssd_data_dir,
                                           cluster_name='ContrailConfigDB')
            db.fixup_cassandra_env_config()
            db_services.append('contrail-database')
        for svc in db_services:
            if self.pdist in ['Ubuntu'] and self.pdistversion == '16.04':
                local('sudo systemctl enable %s' % svc)
                local('sudo systemctl restart %s' % svc)
            else:
                local('sudo chkconfig %s on' % svc)
                local('sudo service %s restart' % svc)

    def setup(self):
        self.disable_selinux()
        self.disable_iptables()
        self.setup_coredump()
        self.setup_database()
        self.fixup_config_files()
        self.run_services()
