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
from oslo.config import cfg
from stevedore import driver

from cloudkitty import config  # noqa
from cloudkitty.openstack.common import importutils as i_utils
from cloudkitty import service
from cloudkitty import write_orchestrator

CONF = cfg.CONF
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


def load_storage_backend():
    storage_args = {'period': CONF.collect.period}
    CONF.import_opt('backend', 'cloudkitty.storage', 'storage')
    backend = driver.DriverManager(
        STORAGES_NAMESPACE,
        CONF.storage.backend,
        invoke_on_load=True,
        invoke_kwds=storage_args).driver
    return backend


def load_output_backend():
    CONF.import_opt('backend', 'cloudkitty.config', 'output')
    backend = i_utils.import_class(CONF.output.backend)
    return backend


def main():
    service.prepare_service()
    output_backend = load_output_backend()
    storage_backend = load_storage_backend()

    wo = write_orchestrator.WriteOrchestrator(output_backend,
                                              'writer',
                                              storage_backend)
    wo.init_writing_pipeline()
    wo.restart_month()
    wo.process()
