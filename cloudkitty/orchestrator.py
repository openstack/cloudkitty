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
import decimal
import random

import eventlet
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_utils import uuidutils
from stevedore import driver
from tooz import coordination

from cloudkitty import collector
from cloudkitty import config  # noqa
from cloudkitty import extension_manager
from cloudkitty import messaging
from cloudkitty import storage
from cloudkitty import storage_state as state
from cloudkitty import transformer
from cloudkitty import utils as ck_utils

eventlet.monkey_patch()

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

orchestrator_opts = [
    cfg.StrOpt('coordination_url',
               secret=True,
               help='Coordination driver URL',
               default='file:///var/lib/cloudkitty/locks'),
]
CONF.register_opts(orchestrator_opts, group='orchestrator')

CONF.import_opt('backend', 'cloudkitty.fetcher', 'fetcher')

FETCHERS_NAMESPACE = 'cloudkitty.fetchers'
PROCESSORS_NAMESPACE = 'cloudkitty.rating.processors'
COLLECTORS_NAMESPACE = 'cloudkitty.collector.backends'
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


class RatingEndpoint(object):
    target = oslo_messaging.Target(namespace='rating',
                                   version='1.1')

    def __init__(self, orchestrator):
        self._global_reload = False
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

    def reload_modules(self, ctxt):
        LOG.info('Received reload modules command.')
        lock = lockutils.lock('module-reload')
        with lock:
            self._global_reload = True

    def reload_module(self, ctxt, name):
        LOG.info('Received reload command for module %s.', name)
        lock = lockutils.lock('module-reload')
        with lock:
            if name not in self._pending_reload:
                self._pending_reload.append(name)

    def enable_module(self, ctxt, name):
        LOG.info('Received enable command for module %s.', name)
        lock = lockutils.lock('module-state')
        with lock:
            self._module_state[name] = True

    def disable_module(self, ctxt, name):
        LOG.info('Received disable command for module %s.', name)
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
            invoke_kwds={'tenant_id': self._tenant_id})

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
                    price += data.get('rating', {}).get('price',
                                                        decimal.Decimal(0))
        return price


class Worker(BaseWorker):
    def __init__(self, collector, storage, tenant_id):
        self._collector = collector
        self._storage = storage
        self._period = CONF.collect.period
        self._wait_time = CONF.collect.wait_periods * self._period
        self._tenant_id = tenant_id
        self._conf = ck_utils.load_conf(CONF.collect.metrics_conf)
        self._state = state.StateManager()

        super(Worker, self).__init__(self._tenant_id)

    def _collect(self, metric, start_timestamp):
        next_timestamp = start_timestamp + self._period

        raw_data = self._collector.retrieve(
            metric,
            start_timestamp,
            next_timestamp,
            self._tenant_id,
        )

        if raw_data:
            return [{'period': {'begin': start_timestamp,
                                'end': next_timestamp},
                     'usage': raw_data}]

    def check_state(self):
        timestamp = self._state.get_state(self._tenant_id)
        return ck_utils.check_time_state(timestamp,
                                         self._period,
                                         CONF.collect.wait_periods)

    def run(self):
        while True:
            timestamp = self.check_state()
            if not timestamp:
                break

            metrics = list(self._conf['metrics'].keys())

            storage_data = []
            for metric in metrics:
                try:
                    try:
                        data = self._collect(metric, timestamp)
                    except collector.NoDataCollected:
                        raise
                    except Exception as e:
                        LOG.warning(
                            'Error while collecting metric '
                            '%(metric)s: %(error)s',
                            {'metric': metric, 'error': e})
                        raise collector.NoDataCollected('', metric)
                except collector.NoDataCollected:
                    LOG.info(
                        'No data collected for metric {} '
                        'at timestamp {}'.format(
                            metric, ck_utils.ts2dt(timestamp))
                    )
                else:
                    # Rating
                    for processor in self._processors:
                        processor.obj.process(data)
                    # Writing
                    if isinstance(data, list):
                        storage_data += data
                    else:
                        storage_data.append(data)

            # We're getting a full period so we directly commit
            self._storage.push(storage_data, self._tenant_id)
            self._state.set_state(self._tenant_id, timestamp)


class Orchestrator(object):
    def __init__(self):
        self.fetcher = driver.DriverManager(
            FETCHERS_NAMESPACE,
            CONF.fetcher.backend,
            invoke_on_load=True,
        ).driver

        transformers = transformer.get_transformers()
        self.collector = collector.get_collector(transformers)
        self.storage = storage.get_storage()
        self._state = state.StateManager()

        # RPC
        self.server = None
        self._rating_endpoint = RatingEndpoint(self)
        self._init_messaging()

        # DLM
        self.coord = coordination.get_coordinator(
            CONF.orchestrator.coordination_url,
            uuidutils.generate_uuid().encode('ascii'))
        self.coord.start()

    def _lock(self, tenant_id):
        lock_name = b"cloudkitty-" + str(tenant_id).encode('ascii')
        return self.coord.get_lock(lock_name)

    def _init_messaging(self):
        target = oslo_messaging.Target(topic='cloudkitty',
                                       server=CONF.host,
                                       version='1.0')
        endpoints = [
            self._rating_endpoint,
        ]
        self.server = messaging.get_server(target, endpoints)
        self.server.start()

    def _check_state(self, tenant_id):
        timestamp = self._state.get_state(tenant_id)
        return ck_utils.check_time_state(timestamp,
                                         CONF.collect.period,
                                         CONF.collect.wait_periods)

    def process_messages(self):
        # TODO(sheeprine): Code kept to handle threading and asynchronous
        # reloading
        # pending_reload = self._rating_endpoint.get_reload_list()
        # pending_states = self._rating_endpoint.get_module_state()
        pass

    def process(self):
        while True:
            self.tenants = self.fetcher.get_tenants()
            random.shuffle(self.tenants)
            LOG.info('Tenants loaded for fetcher %s', self.fetcher.name)

            for tenant_id in self.tenants:

                lock = self._lock(tenant_id)
                if lock.acquire(blocking=False):
                    state = self._check_state(tenant_id)
                    if state:
                        worker = Worker(
                            self.collector,
                            self.storage,
                            tenant_id,
                        )
                        worker.run()

                    lock.release()

                self.coord.heartbeat()
                # NOTE(sheeprine): Slow down looping if all tenants are
                # being processed
                eventlet.sleep(1)
            # FIXME(sheeprine): We may cause a drift here
            eventlet.sleep(CONF.collect.period)

    def terminate(self):
        self.coord.stop()
