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
from datetime import timedelta
import decimal
import functools
import hashlib
import multiprocessing
import random
import sys
import time

import cotyledon
import futurist
from futurist import waiters
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_utils import uuidutils
from stevedore import driver
from tooz import coordination

from cloudkitty import collector
from cloudkitty import config  # noqa
from cloudkitty import dataframe
from cloudkitty import extension_manager
from cloudkitty import messaging
from cloudkitty import storage
from cloudkitty import storage_state as state
from cloudkitty import utils as ck_utils
from cloudkitty.utils import tz as tzutils


LOG = logging.getLogger(__name__)

CONF = cfg.CONF

orchestrator_opts = [
    cfg.StrOpt(
        'coordination_url',
        secret=True,
        help='Coordination driver URL',
        default='file:///var/lib/cloudkitty/locks'),
    cfg.IntOpt(
        'max_workers',
        default=multiprocessing.cpu_count(),
        sample_default=4,
        min=1,
        help='Max nb of workers to run. Defaults to the nb of available CPUs'),
    cfg.IntOpt('max_threads',
               # NOTE(peschk_l): This is the futurist default
               default=multiprocessing.cpu_count() * 5,
               sample_default=20,
               min=1,
               deprecated_name='max_greenthreads',
               advanced=True,
               help='Maximal number of threads to use per worker. Defaults to '
               '5 times the nb of available CPUs'),
]

CONF.register_opts(orchestrator_opts, group='orchestrator')

CONF.import_opt('backend', 'cloudkitty.fetcher', 'fetcher')

FETCHERS_NAMESPACE = 'cloudkitty.fetchers'
PROCESSORS_NAMESPACE = 'cloudkitty.rating.processors'
COLLECTORS_NAMESPACE = 'cloudkitty.collector.backends'
STORAGES_NAMESPACE = 'cloudkitty.storage.backends'


def get_lock(coord, tenant_id):
    name = hashlib.sha256(
        ("cloudkitty-"
         + str(tenant_id + '-')
         + str(CONF.collect.collector + '-')
         + str(CONF.fetcher.backend + '-')
         + str(CONF.collect.scope_key)).encode('ascii')).hexdigest()
    return name, coord.get_lock(name.encode('ascii'))


class RatingEndpoint(object):
    target = oslo_messaging.Target(namespace='rating',
                                   version='1.0')

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


class ScopeEndpoint(object):
    target = oslo_messaging.Target(version='1.0')

    def __init__(self):
        self._coord = coordination.get_coordinator(
            CONF.orchestrator.coordination_url,
            uuidutils.generate_uuid().encode('ascii'))
        self._state = state.StateManager()
        self._storage = storage.get_storage()
        self._coord.start(start_heart=True)

    def reset_state(self, ctxt, res_data):
        LOG.info('Received state reset command. {}'.format(res_data))
        random.shuffle(res_data['scopes'])
        for scope in res_data['scopes']:
            lock_name, lock = get_lock(self._coord, scope['scope_id'])
            LOG.debug(
                '[ScopeEndpoint] Trying to acquire lock "{}" ...'.format(
                    lock_name,
                )
            )
            if lock.acquire(blocking=True):
                LOG.debug(
                    '[ScopeEndpoint] Acquired lock "{}".'.format(
                        lock_name,
                    )
                )
                state_dt = tzutils.dt_from_iso(res_data['state'])
                try:
                    self._storage.delete(begin=state_dt, end=None, filters={
                        scope['scope_key']: scope['scope_id'],
                    })
                    self._state.set_state(
                        scope['scope_id'],
                        state_dt,
                        fetcher=scope['fetcher'],
                        collector=scope['collector'],
                        scope_key=scope['scope_key'],
                    )
                finally:
                    lock.release()
                    LOG.debug(
                        '[ScopeEndpoint] Released lock "{}" .'.format(
                            lock_name,
                        )
                    )


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


def _check_state(obj, period, tenant_id):
    timestamp = obj._state.get_state(tenant_id)
    return ck_utils.check_time_state(timestamp,
                                     period,
                                     CONF.collect.wait_periods)


class Worker(BaseWorker):
    def __init__(self, collector, storage, tenant_id, worker_id):
        self._collector = collector
        self._storage = storage
        self._period = CONF.collect.period
        self._wait_time = CONF.collect.wait_periods * self._period
        self._tenant_id = tenant_id
        self._worker_id = worker_id
        self._log_prefix = '[scope: {scope}, worker: {worker}] '.format(
            scope=self._tenant_id, worker=self._worker_id)
        self._conf = ck_utils.load_conf(CONF.collect.metrics_conf)
        self._state = state.StateManager()
        self._check_state = functools.partial(
            _check_state, self, self._period, self._tenant_id)

        super(Worker, self).__init__(self._tenant_id)

    def _collect(self, metric, start_timestamp):
        next_timestamp = tzutils.add_delta(
            start_timestamp, timedelta(seconds=self._period))

        name, data = self._collector.retrieve(
            metric,
            start_timestamp,
            next_timestamp,
            self._tenant_id,
        )
        if not data:
            raise collector.NoDataCollected

        return name, data

    def _do_collection(self, metrics, timestamp):

        def _get_result(metric):
            try:
                return self._collect(metric, timestamp)
            except collector.NoDataCollected:
                LOG.info(
                    self._log_prefix + 'No data collected '
                    'for metric {metric} at timestamp {ts}'.format(
                        metric=metric, ts=timestamp))
                return metric, None
            except Exception as e:
                LOG.exception(
                    self._log_prefix + 'Error while collecting'
                    ' metric {metric} at timestamp {ts}: {e}. Exiting.'.format(
                        metric=metric, ts=timestamp, e=e))
                # FIXME(peschk_l): here we just exit, and the
                # collection will be retried during the next collect
                # cycle. In the future, we should implement a retrying
                # system in workers
                sys.exit(1)

        with futurist.ThreadPoolExecutor(
                max_workers=CONF.orchestrator.max_threads) as tpool:
            futs = [tpool.submit(_get_result, metric) for metric in metrics]
            LOG.debug(self._log_prefix +
                      'Collecting {} metrics.'.format(len(metrics)))
            results = [r.result() for r in waiters.wait_for_all(futs).done]
            LOG.debug(self._log_prefix + 'Collecting {} metrics took {}s '
                      'total, with {}s average'.format(
                          tpool.statistics.executed,
                          tpool.statistics.runtime,
                          tpool.statistics.average_runtime))
        return dict(filter(lambda x: x[1] is not None, results))

    def run(self):
        while True:
            timestamp = self._check_state()
            if not timestamp:
                break

            metrics = list(self._conf['metrics'].keys())

            # Collection
            usage_data = self._do_collection(metrics, timestamp)

            frame = dataframe.DataFrame(
                start=timestamp,
                end=tzutils.add_delta(timestamp,
                                      timedelta(seconds=self._period)),
                usage=usage_data,
            )
            # Rating
            for processor in self._processors:
                frame = processor.obj.process(frame)

            # Writing
            self._storage.push([frame], self._tenant_id)
            self._state.set_state(self._tenant_id, timestamp)


class Orchestrator(cotyledon.Service):
    def __init__(self, worker_id):
        self._worker_id = worker_id
        super(Orchestrator, self).__init__(self._worker_id)

        self.fetcher = driver.DriverManager(
            FETCHERS_NAMESPACE,
            CONF.fetcher.backend,
            invoke_on_load=True,
        ).driver

        self.collector = collector.get_collector()
        self.storage = storage.get_storage()
        self._state = state.StateManager()

        # RPC
        self.server = None
        self._rating_endpoint = RatingEndpoint(self)
        self._scope_endpoint = ScopeEndpoint()
        self._init_messaging()

        # DLM
        self.coord = coordination.get_coordinator(
            CONF.orchestrator.coordination_url,
            uuidutils.generate_uuid().encode('ascii'))
        self.coord.start(start_heart=True)
        self._check_state = functools.partial(
            _check_state, self, CONF.collect.period)

    def _init_messaging(self):
        target = oslo_messaging.Target(topic='cloudkitty',
                                       server=CONF.host,
                                       version='1.0')
        endpoints = [
            self._rating_endpoint,
            self._scope_endpoint,
        ]
        self.server = messaging.get_server(target, endpoints)
        self.server.start()

    def process_messages(self):
        # TODO(sheeprine): Code kept to handle threading and asynchronous
        # reloading
        # pending_reload = self._rating_endpoint.get_reload_list()
        # pending_states = self._rating_endpoint.get_module_state()
        pass

    def run(self):
        LOG.debug('Started worker {}.'.format(self._worker_id))
        while True:
            self.tenants = self.fetcher.get_tenants()
            random.shuffle(self.tenants)
            LOG.info('[Worker: {w}] Tenants loaded for fetcher {f}'.format(
                w=self._worker_id, f=self.fetcher.name))

            for tenant_id in self.tenants:

                lock_name, lock = get_lock(self.coord, tenant_id)
                LOG.debug(
                    '[Worker: {w}] Trying to acquire lock "{lck}" ...'.format(
                        w=self._worker_id, lck=lock_name)
                )
                if lock.acquire(blocking=False):
                    LOG.debug(
                        '[Worker: {w}] Acquired lock "{lck}" ...'.format(
                            w=self._worker_id, lck=lock_name)
                    )
                    state = self._check_state(tenant_id)
                    if state:
                        worker = Worker(
                            self.collector,
                            self.storage,
                            tenant_id,
                            self._worker_id,
                        )
                        worker.run()

                    lock.release()

            # FIXME(sheeprine): We may cause a drift here
            time.sleep(CONF.collect.period)

    def terminate(self):
        LOG.debug('Terminating worker {}...'.format(self._worker_id))
        self.coord.stop()
        LOG.debug('Terminated worker {}.'.format(self._worker_id))


class OrchestratorServiceManager(cotyledon.ServiceManager):

    def __init__(self):
        super(OrchestratorServiceManager, self).__init__()
        self.service_id = self.add(Orchestrator,
                                   workers=CONF.orchestrator.max_workers)
