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
import decimal

import eventlet
from oslo.config import cfg
from oslo_concurrency import lockutils
from oslo_log import log as logging
import oslo_messaging as messaging
import six
from stevedore import driver
from stevedore import extension

from cloudkitty import collector
from cloudkitty.common import rpc
from cloudkitty import config  # noqa
from cloudkitty import extension_manager
from cloudkitty import utils as ck_utils

eventlet.monkey_patch()

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('backend', 'cloudkitty.storage', 'storage')
CONF.import_opt('backend', 'cloudkitty.tenant_fetcher', 'tenant_fetcher')

COLLECTORS_NAMESPACE = 'cloudkitty.collector.backends'
FETCHERS_NAMESPACE = 'cloudkitty.tenant.fetchers'
TRANSFORMERS_NAMESPACE = 'cloudkitty.transformers'
PROCESSORS_NAMESPACE = 'cloudkitty.rating.processors'
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


class RatingEndpoint(object):
    target = messaging.Target(namespace='rating',
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
        worker = APIWorker()
        return str(worker.quote(res_data))

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


class BaseWorker(object):
    def __init__(self, tenant_id=None):
        self._tenant_id = tenant_id

        # Rating processors
        self._processors = []
        self._load_rating_processors()

    def _load_rating_processors(self):
        self._processors = []
        processors = extension_manager.EnabledExtensionManager(
            PROCESSORS_NAMESPACE,
            invoke_kwds={'tenant_id': self._tenant_id}
        )

        for processor in processors:
            self._processors.append(processor)
        self._processors.sort(key=lambda x: x.obj.priority, reverse=True)


class APIWorker(BaseWorker):
    def __init__(self, tenant_id=None):
        super(APIWorker, self).__init__(tenant_id)

    def quote(self, res_data):
        for processor in self._processors:
            processor.obj.quote(res_data)

        price = decimal.Decimal(0)
        for res in res_data:
            for res_usage in res['usage'].values():
                for data in res_usage:
                    price += data.get('rating', {}).get('price', 0.0)
        return price


class Worker(BaseWorker):
    def __init__(self, collector, storage, tenant_id=None):
        self._collector = collector
        self._storage = storage

        self._period = CONF.collect.period
        self._wait_time = CONF.collect.wait_periods * self._period

        super(Worker, self).__init__(tenant_id)

    def _collect(self, service, start_timestamp):
        next_timestamp = start_timestamp + self._period
        raw_data = self._collector.retrieve(service,
                                            start_timestamp,
                                            next_timestamp,
                                            self._tenant_id)

        timed_data = [{'period': {'begin': start_timestamp,
                                  'end': next_timestamp},
                      'usage': raw_data}]
        return timed_data

    def check_state(self):
        timestamp = self._storage.get_state(self._tenant_id)
        if not timestamp:
            month_start = ck_utils.get_month_start()
            return ck_utils.dt2ts(month_start)

        now = ck_utils.utcnow_ts()
        next_timestamp = timestamp + self._period
        if next_timestamp + self._wait_time < now:
            return next_timestamp
        return 0

    def run(self):
        while True:
            timestamp = self.check_state()
            if not timestamp:
                break

            for service in CONF.collect.services:
                try:
                    try:
                        data = self._collect(service, timestamp)
                    except collector.NoDataCollected:
                        raise
                    except Exception as e:
                        LOG.warn('Error while collecting service {service}:'
                                 ' {error}'.format(service=service,
                                                   error=six.text_type(e)))
                        raise collector.NoDataCollected('', service)
                except collector.NoDataCollected:
                    begin = timestamp
                    end = begin + self._period
                    for processor in self._processors:
                        processor.obj.nodata(begin, end)
                    self._storage.nodata(begin, end, self._tenant_id)
                else:
                    # Rating
                    for processor in self._processors:
                        processor.obj.process(data)
                    # Writing
                    self._storage.append(data, self._tenant_id)

            # We're getting a full period so we directly commit
            self._storage.commit(self._tenant_id)


class Orchestrator(object):
    def __init__(self):
        # Tenant fetcher
        self.fetcher = driver.DriverManager(
            FETCHERS_NAMESPACE,
            CONF.tenant_fetcher.backend,
            invoke_on_load=True).driver

        # Transformers
        self.transformers = {}
        self._load_transformers()

        collector_args = {'transformers': self.transformers,
                          'period': CONF.collect.period}
        self.collector = driver.DriverManager(
            COLLECTORS_NAMESPACE,
            CONF.collect.collector,
            invoke_on_load=True,
            invoke_kwds=collector_args).driver

        storage_args = {'period': CONF.collect.period}
        self.storage = driver.DriverManager(
            STORAGES_NAMESPACE,
            CONF.storage.backend,
            invoke_on_load=True,
            invoke_kwds=storage_args).driver

        # RPC
        self.server = None
        self._rating_endpoint = RatingEndpoint(self)
        self._init_messaging()

    def _load_tenant_list(self):
        self._tenants = self.fetcher.get_tenants()

    def _init_messaging(self):
        target = messaging.Target(topic='cloudkitty',
                                  server=CONF.host,
                                  version='1.0')
        endpoints = [
            self._rating_endpoint,
        ]
        self.server = rpc.get_server(target, endpoints)
        self.server.start()

    def _check_state(self, tenant_id):
        timestamp = self.storage.get_state(tenant_id)
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

    def process_messages(self):
        # TODO(sheeprine): Code kept to handle threading and asynchronous
        # reloading
        # pending_reload = self._rating_endpoint.get_reload_list()
        # pending_states = self._rating_endpoint.get_module_state()
        pass

    def process(self):
        while True:
            self.process_messages()
            self._load_tenant_list()
            while len(self._tenants):
                for tenant in self._tenants:
                    if not self._check_state(tenant):
                        self._tenants.remove(tenant)
                    else:
                        worker = Worker(self.collector,
                                        self.storage,
                                        tenant)
                        worker.run()
            # FIXME(sheeprine): We may cause a drift here
            eventlet.sleep(CONF.collect.period)

    def terminate(self):
        pass
