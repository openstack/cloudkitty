# -*- coding: utf-8 -*-
# !/usr/bin/env python
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
import eventlet
from keystoneclient.v2_0 import client as kclient
from oslo.config import cfg
from oslo import messaging
from stevedore import driver
from stevedore import extension

from cloudkitty.common import rpc
from cloudkitty import config  # NOQA
from cloudkitty import extension_manager
from cloudkitty.openstack.common import lockutils
from cloudkitty.openstack.common import log as logging
from cloudkitty import state
from cloudkitty import utils as ck_utils

eventlet.monkey_patch()

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

COLLECTORS_NAMESPACE = 'cloudkitty.collector.backends'
TRANSFORMERS_NAMESPACE = 'cloudkitty.transformers'
PROCESSORS_NAMESPACE = 'cloudkitty.billing.processors'
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


class BillingEndpoint(object):
    target = messaging.Target(namespace='billing',
                              version='1.0')

    def __init__(self, orchestrator):
        self._pending_reload = []
        self._module_state = {}
        self._orchestrator = orchestrator

    def get_reload_list(self):
        lock = lockutils.lock('module-reload')
        with lock:
            reload_list = self._pending_reload
            self._pending_reload = []
            return reload_list

    def get_module_state(self):
        lock = lockutils.lock('module-state')
        with lock:
            module_list = self._module_state
            self._module_state = {}
            return module_list

    def quote(self, ctxt, res_data):
        LOG.debug('Received quote from RPC.')
        return self._orchestrator.process_quote(res_data)

    def reload_module(self, ctxt, name):
        LOG.info('Received reload command for module {}.'.format(name))
        lock = lockutils.lock('module-reload')
        with lock:
            if name not in self._pending_reload:
                self._pending_reload.append(name)

    def enable_module(self, ctxt, name):
        LOG.info('Received enable command for module {}.'.format(name))
        lock = lockutils.lock('module-state')
        with lock:
            self._module_state[name] = True

    def disable_module(self, ctxt, name):
        LOG.info('Received disable command for module {}.'.format(name))
        lock = lockutils.lock('module-state')
        with lock:
            self._module_state[name] = False
            if name in self._pending_reload:
                self._pending_reload.remove(name)


class Orchestrator(object):
    def __init__(self):
        self.keystone = kclient.Client(username=CONF.auth.username,
                                       password=CONF.auth.password,
                                       tenant_name=CONF.auth.tenant,
                                       region_name=CONF.auth.region,
                                       auth_url=CONF.auth.url)

        self.sm = state.DBStateManager(self.keystone.user_id,
                                       'osrtf')

        # Transformers
        self.transformers = {}
        self._load_transformers()

        collector_args = {'transformers': self.transformers,
                          'user': CONF.auth.username,
                          'password': CONF.auth.password,
                          'tenant': CONF.auth.tenant,
                          'region': CONF.auth.region,
                          'keystone_url': CONF.auth.url,
                          'period': CONF.collect.period}
        self.collector = driver.DriverManager(
            COLLECTORS_NAMESPACE,
            CONF.collect.collector,
            invoke_on_load=True,
            invoke_kwds=collector_args).driver

        CONF.import_opt('backend', 'cloudkitty.storage', 'storage')
        storage_args = {'period': CONF.collect.period}
        self.storage = driver.DriverManager(
            STORAGES_NAMESPACE,
            CONF.storage.backend,
            invoke_on_load=True,
            invoke_kwds=storage_args).driver

        # Billing processors
        self.b_processors = {}
        self._load_billing_processors()

        # RPC
        self.server = None
        self._billing_endpoint = BillingEndpoint(self)
        self._init_messaging()

    def _init_messaging(self):
        target = messaging.Target(topic='cloudkitty',
                                  server=CONF.host,
                                  version='1.0')
        endpoints = [
            self._billing_endpoint,
        ]
        self.server = rpc.get_server(target, endpoints)
        self.server.start()

    def _check_state(self):
        timestamp = self.storage.get_state()
        if not timestamp:
            month_start = ck_utils.get_month_start()
            return ck_utils.dt2ts(month_start)

        now = ck_utils.utcnow_ts()
        next_timestamp = timestamp + CONF.collect.period
        wait_time = CONF.collect.wait_periods * CONF.collect.period
        if next_timestamp + wait_time < now:
            return next_timestamp
        return 0

    def _collect(self, service, start_timestamp):
        next_timestamp = start_timestamp + CONF.collect.period
        raw_data = self.collector.retrieve(service,
                                           start_timestamp,
                                           next_timestamp)

        timed_data = [{'period': {'begin': start_timestamp,
                                  'end': next_timestamp},
                      'usage': raw_data}]
        return timed_data

    def _load_transformers(self):
        self.transformers = {}
        transformers = extension.ExtensionManager(
            TRANSFORMERS_NAMESPACE,
            invoke_on_load=True)

        for transformer in transformers:
            t_name = transformer.name
            t_obj = transformer.obj
            self.transformers[t_name] = t_obj

    def _load_billing_processors(self):
        self.b_processors = {}
        processors = extension_manager.EnabledExtensionManager(
            PROCESSORS_NAMESPACE,
        )

        for processor in processors:
            b_name = processor.name
            b_obj = processor.obj
            self.b_processors[b_name] = b_obj

    def process_quote(self, res_data):
        for processor in self.b_processors.values():
            processor.process(res_data)

        price = 0.0
        for res in res_data:
            for res_usage in res['usage'].values():
                for data in res_usage:
                    price += data.get('billing', {}).get('price', 0.0)
        return price

    def process_messages(self):
        pending_reload = self._billing_endpoint.get_reload_list()
        pending_states = self._billing_endpoint.get_module_state()
        for name in pending_reload:
            if name in self.b_processors:
                if name in self.b_processors.keys():
                    LOG.info('Reloading configuration of {} module.'.format(
                        name))
                    self.b_processors[name].reload_config()
                else:
                    LOG.info('Tried to reload a disabled module: {}.'.format(
                        name))
        for name, status in pending_states.items():
            if name in self.b_processors and not status:
                LOG.info('Disabling {} module.'.format(name))
                self.b_processors.pop(name)
            else:
                LOG.info('Enabling {} module.'.format(name))
                processors = extension_manager.EnabledExtensionManager(
                    PROCESSORS_NAMESPACE)
                for processor in processors:
                    if processor.name == name:
                        self.b_processors[name] = processor

    def process(self):
        while True:
            self.process_messages()
            timestamp = self._check_state()
            if not timestamp:
                eventlet.sleep(CONF.collect.period)
                continue

            for service in CONF.collect.services:
                data = self._collect(service, timestamp)

                # Billing
                for processor in self.b_processors.values():
                    processor.process(data)

                # Writing
                self.storage.append(data)

            # We're getting a full period so we directly commit
            self.storage.commit()

    def terminate(self):
        pass
