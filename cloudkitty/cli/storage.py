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
from oslo_config import cfg
from stevedore import driver

from cloudkitty import config  # noqa
from cloudkitty import service

CONF = cfg.CONF
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


def init_storage_backend():
    CONF.import_opt('backend', 'cloudkitty.storage', 'storage')
    backend = driver.DriverManager(
        STORAGES_NAMESPACE,
        CONF.storage.backend)
    backend.driver.init()


def main():
    service.prepare_service()
    init_storage_backend()
