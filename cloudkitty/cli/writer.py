# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Stéphane Albert
#
from __future__ import print_function

from oslo_config import cfg
from oslo_utils import importutils as i_utils
from stevedore import driver

from cloudkitty import config  # noqa
from cloudkitty import service
from cloudkitty import write_orchestrator

CONF = cfg.CONF
CONF.import_opt('period', 'cloudkitty.collector', 'collect')
CONF.import_opt('backend', 'cloudkitty.config', 'output')
CONF.import_opt('basepath', 'cloudkitty.config', 'output')
CONF.import_opt('backend', 'cloudkitty.storage', 'storage')
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


class DBCommand(object):

    def __init__(self):
        self._storage = None
        self._output = None
        self._load_storage_backend()
        self._load_output_backend()

    def _load_storage_backend(self):
        storage_args = {'period': CONF.collect.period}
        backend = driver.DriverManager(
            STORAGES_NAMESPACE,
            CONF.storage.backend,
            invoke_on_load=True,
            invoke_kwds=storage_args).driver
        self._storage = backend

    def _load_output_backend(self):
        backend = i_utils.import_class(CONF.output.backend)
        self._output = backend

    def generate(self):
        if not CONF.command.tenant:
            tenants = self._storage.get_tenants(CONF.command.begin,
                                                CONF.command.end)
        else:
            tenants = [CONF.command.tenant]
        for tenant in tenants:
            wo = write_orchestrator.WriteOrchestrator(self._output,
                                                      tenant,
                                                      self._storage,
                                                      CONF.output.basepath)
            wo.init_writing_pipeline()
            if not CONF.command.begin:
                wo.restart_month()
            wo.process()

    def tenants_list(self):
        tenants = self._storage.get_tenants(CONF.command.begin,
                                            CONF.command.end)
        print('Tenant list:')
        for tenant in tenants:
            print(tenant)


def add_command_parsers(subparsers):
    command_object = DBCommand()

    parser = subparsers.add_parser('generate')
    parser.set_defaults(func=command_object.generate)
    parser.add_argument('--tenant', nargs='?')
    parser.add_argument('--begin', nargs='?')
    parser.add_argument('--end', nargs='?')

    parser = subparsers.add_parser('tenants_list')
    parser.set_defaults(func=command_object.tenants_list)
    parser.add_argument('--begin', nargs='?')
    parser.add_argument('--end', nargs='?')


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help='Available commands',
                                handler=add_command_parsers)

CONF.register_cli_opt(command_opt)


def main():
    service.prepare_service()
    CONF.command.func()
