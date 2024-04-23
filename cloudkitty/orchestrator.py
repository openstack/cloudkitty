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
import copy

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
        help='Coordination backend URL',
        default='file:///var/lib/cloudkitty/locks'),
    cfg.IntOpt(
        'max_workers',
        default=multiprocessing.cpu_count(),
        sample_default=4,
        min=0,
        help='Max number of workers to execute the rating process. Defaults '
             'to the number of available CPU cores.'),
    cfg.IntOpt(
        'max_workers_reprocessing',
        default=multiprocessing.cpu_count(),
        min=0,
        help='Max number of workers to execute the reprocessing. Defaults to '
             'the number of available CPU cores.'),
    cfg.IntOpt('max_threads',
               # NOTE(peschk_l): This is the futurist default
               default=multiprocessing.cpu_count() * 5,
               sample_default=20,
               min=1,
               deprecated_name='max_greenthreads',
               advanced=True,
               help='Maximal number of threads to use per worker. Defaults to '
               '5 times the number of available CPUs'),
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
        LOG.debug('Received quote request [%s] from RPC.', res_data)
        worker = APIWorker()

        start = tzutils.localized_now()
        end = tzutils.add_delta(start, timedelta(seconds=CONF.collect.period))

        # Need to prepare data to support the V2 processing format
        usage = {}
        for k in res_data['usage']:
            all_data_points_for_metric = []
            all_quote_data_entries = res_data['usage'][k]
            for p in all_quote_data_entries:
                vol = p['vol']
                desc = p.get('desc', {})

                data_point = dataframe.DataPoint(
                    vol['unit'],
                    vol['qty'],
                    0,
                    desc.get('groupby', []),
                    desc.get('metadata', []),
                )
                all_data_points_for_metric.append(data_point)
            usage[k] = all_data_points_for_metric

        frame = dataframe.DataFrame(
            start=start,
            end=end,
            usage=usage,
        )

        quote_result = worker.quote(frame)
        LOG.debug("Quote result [%s] for input data [%s].",
                  quote_result, res_data)
        return str(quote_result)

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
                last_processed_timestamp = tzutils.dt_from_iso(
                    res_data['last_processed_timestamp'])
                try:
                    self._storage.delete(
                        begin=last_processed_timestamp, end=None, filters={
                            scope['scope_key']: scope['scope_id']})
                    self._state.set_last_processed_timestamp(
                        scope['scope_id'],
                        last_processed_timestamp,
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
        quote_result = res_data
        for processor in self._processors:
            quote_result = processor.obj.quote(quote_result)

        price = decimal.Decimal(0)
        for _, point in quote_result.iterpoints():
            price += point.price
        return price


def _check_state(obj, period, tenant_id):
    timestamp = obj._state.get_last_processed_timestamp(tenant_id)
    return ck_utils.check_time_state(timestamp,
                                     period,
                                     CONF.collect.wait_periods)


class Worker(BaseWorker):
    def __init__(self, collector, storage, tenant_id, worker_id):
        super(Worker, self).__init__(tenant_id)

        self._collector = collector
        self._storage = storage
        self._period = CONF.collect.period
        self._wait_time = CONF.collect.wait_periods * self._period
        self._worker_id = worker_id
        self._log_prefix = '[scope: {scope}, worker: {worker}] '.format(
            scope=self._tenant_id, worker=self._worker_id)
        self._conf = ck_utils.load_conf(CONF.collect.metrics_conf)
        self._state = state.StateManager()
        self.next_timestamp_to_process = functools.partial(
            _check_state, self, self._period, self._tenant_id)

        super(Worker, self).__init__(self._tenant_id)

    def _collect(self, metric, start_timestamp):
        next_timestamp = tzutils.add_delta(
            start_timestamp, timedelta(seconds=self._period))

        name, data = self._collector.retrieve(
            metric,
            start_timestamp,
            next_timestamp,
            self._tenant_id
        )
        if not data:
            raise collector.NoDataCollected(self._collector, metric)

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

        return self._do_execute_collection(_get_result, metrics)

    def _do_execute_collection(self, _get_result, metrics):
        """Execute the metric measurement collection

        When executing this method a ZeroDivisionError might be raised.
        This happens when no executions have happened in the
        `futurist.ThreadPoolExecutor`; then, when calling the
        `average_runtime`, the exception is thrown. In such a case, there is
         no need for further actions, and we can ignore the error.

        :param _get_result: the method to execute and get the metrics
        :param metrics: the list of metrics to be collected
        :return: the metrics measurements
        """
        results = []
        try:
            with futurist.ThreadPoolExecutor(
                    max_workers=CONF.orchestrator.max_threads) as tpool:

                futs = [tpool.submit(_get_result, metric)
                        for metric in metrics]

                LOG.debug(self._log_prefix +
                          'Collecting [{}] metrics.'.format(metrics))

                results = [r.result() for r in waiters.wait_for_all(futs).done]

                log_message = self._log_prefix + \
                    "Collecting {} metrics took {}s total, with {}s average"

                LOG.debug(log_message.format(tpool.statistics.executed,
                                             tpool.statistics.runtime,
                                             tpool.statistics.average_runtime))

        except ZeroDivisionError as zeroDivisionError:
            LOG.debug("Ignoring ZeroDivisionError for metrics [%s]: [%s].",
                      metrics, zeroDivisionError)

        return dict(filter(lambda x: x[1] is not None, results))

    def run(self):
        should_continue_processing = self.execute_worker_processing()
        while should_continue_processing:
            should_continue_processing = self.execute_worker_processing()

    def execute_worker_processing(self):
        timestamp = self.next_timestamp_to_process()
        LOG.debug("Processing timestamp [%s] for storage scope [%s].",
                  timestamp, self._tenant_id)
        if not timestamp:
            LOG.debug("Worker [%s] finished processing storage scope [%s].",
                      self._worker_id, self._tenant_id)
            return False
        if self._state.get_last_processed_timestamp(self._tenant_id):
            if not self._state.is_storage_scope_active(self._tenant_id):
                LOG.debug("Skipping processing for storage scope [%s] "
                          "because it is marked as inactive.",
                          self._tenant_id)
                return False
        else:
            LOG.debug("No need to check if [%s] is de-activated. "
                      "We have never processed it before.")
        self.do_execute_scope_processing(timestamp)
        return True

    def do_execute_scope_processing(self, timestamp):
        metrics = list(self._collector.conf.keys())
        # Collection
        metrics = sorted(metrics)
        usage_data = self._do_collection(metrics, timestamp)

        LOG.debug("Usage data [%s] found for storage scope [%s] in "
                  "timestamp [%s].", usage_data, self._tenant_id,
                  timestamp)
        start_time = timestamp
        end_time = tzutils.add_delta(timestamp,
                                     timedelta(seconds=self._period))
        # No usage records found in
        if not usage_data:
            LOG.warning("No usage data for storage scope [%s] on "
                        "timestamp [%s]. You might want to consider "
                        "de-activating it.", self._tenant_id, timestamp)

        else:
            frame = self.execute_measurements_rating(end_time, start_time,
                                                     usage_data)
            self.persist_rating_data(end_time, frame, start_time)

        self.update_scope_processing_state_db(timestamp)

    def persist_rating_data(self, end_time, frame, start_time):
        LOG.debug("Persisting processed frames [%s] for scope [%s] and time "
                  "[start=%s,end=%s]", frame, self._tenant_id, start_time,
                  end_time)

        self._storage.push([frame], self._tenant_id)

    def execute_measurements_rating(self, end_time, start_time, usage_data):
        frame = dataframe.DataFrame(
            start=start_time,
            end=end_time,
            usage=usage_data,
        )

        for processor in self._processors:
            original_data = copy.deepcopy(frame)
            frame = processor.obj.process(frame)
            LOG.debug("Results [%s] for processing [%s] of data points [%s].",
                      frame, processor.obj.process, original_data)
        return frame

    def update_scope_processing_state_db(self, timestamp):
        self._state.set_state(self._tenant_id, timestamp)


class ReprocessingWorker(Worker):
    def __init__(self, collector, storage, tenant_id, worker_id):
        self.scope = tenant_id
        self.scope_key = None

        super(ReprocessingWorker, self).__init__(
            collector, storage, self.scope.identifier, worker_id)

        self.reprocessing_scheduler_db = state.ReprocessingSchedulerDb()
        self.next_timestamp_to_process = self._next_timestamp_to_process

        self.load_scope_key()

    def load_scope_key(self):
        scope_from_db = self._state.get_all(self._tenant_id)

        if len(scope_from_db) < 1:
            raise Exception("Scope [%s] scheduled for reprocessing does not "
                            "seem to exist anymore." % self.scope)

        if len(scope_from_db) > 1:
            raise Exception("Unexpected number of storage state entries found "
                            "for scope [%s]." % self.scope)

        self.scope_key = scope_from_db[0].scope_key

    def _next_timestamp_to_process(self):
        db_item = self.reprocessing_scheduler_db.get_from_db(
            identifier=self.scope.identifier,
            start_reprocess_time=self.scope.start_reprocess_time,
            end_reprocess_time=self.scope.end_reprocess_time)

        if not db_item:
            LOG.info("It seems that the processing for schedule [%s] was "
                     "finished by other worker.", self.scope)
            return None

        return ReprocessingWorker.generate_next_timestamp(
            db_item, self._period)

    @staticmethod
    def generate_next_timestamp(db_item, processing_period_interval):
        new_timestamp = db_item.start_reprocess_time
        if db_item.current_reprocess_time:
            period_delta = timedelta(seconds=processing_period_interval)

            new_timestamp = db_item.current_reprocess_time + period_delta

            LOG.debug("Current reprocessed time is [%s], therefore, the next "
                      "one to process is [%s] based on the processing "
                      "interval [%s].", db_item.start_reprocess_time,
                      new_timestamp, processing_period_interval)
        else:
            LOG.debug("There is no reprocessing for the schedule [%s]. "
                      "Therefore, we use the start time [%s] as the first "
                      "time to process.", db_item, new_timestamp)
        if new_timestamp <= db_item.end_reprocess_time:
            return tzutils.local_to_utc(new_timestamp)
        else:
            LOG.debug("No need to keep reprocessing schedule [%s] as we "
                      "processed all requested timestamps.", db_item)
            return None

    def do_execute_scope_processing(self, timestamp):
        end_of_this_processing = timestamp + timedelta(seconds=self._period)

        end_of_this_processing = tzutils.local_to_utc(end_of_this_processing)

        # If the start_reprocess_time of the reprocessing task equals to
        # the current reprocessing time, it means that we have just started
        # executing it. Therefore, we can clean/erase the old data in the
        # reprocessing task time frame.
        if tzutils.local_to_utc(self.scope.start_reprocess_time) == timestamp:
            LOG.info(
                "Cleaning backend [%s] data for reprocessing scope [%s] for "
                "timeframe[start=%s, end=%s].", self._storage, self.scope,
                self.scope.start_reprocess_time, self.scope.end_reprocess_time)
            self._storage.delete(
                begin=self.scope.start_reprocess_time,
                end=self.scope.end_reprocess_time,
                filters={self.scope_key: self._tenant_id})
        else:
            LOG.debug("No need to clean backend [%s] data for reprocessing "
                      "scope [%s] for timeframe[start=%s, end=%s]. We are "
                      "past the very first timestamp; therefore, the cleaning "
                      "for the reprocessing task period has already been "
                      "executed.", self._storage, self.scope,
                      self.scope.start_reprocess_time,
                      self.scope.end_reprocess_time)

        LOG.debug("Executing the reprocessing of scope [%s] for "
                  "timeframe[start=%s, end=%s].", self.scope, timestamp,
                  end_of_this_processing)

        super(ReprocessingWorker, self).do_execute_scope_processing(timestamp)

    def update_scope_processing_state_db(self, timestamp):
        LOG.debug("After data is persisted in the storage backend [%s], we "
                  "will update the scope [%s] current processing time to "
                  "[%s].", self._storage, self.scope, timestamp)
        self.reprocessing_scheduler_db.update_reprocessing_time(
            identifier=self.scope.identifier,
            start_reprocess_time=self.scope.start_reprocess_time,
            end_reprocess_time=self.scope.end_reprocess_time,
            new_current_time_stamp=timestamp)


class CloudKittyProcessor(cotyledon.Service):
    def __init__(self, worker_id):
        self._worker_id = worker_id
        super(CloudKittyProcessor, self).__init__(self._worker_id)

        self.tenants = []

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
        self.next_timestamp_to_process = functools.partial(
            _check_state, self, CONF.collect.period)

        self.worker_class = Worker
        self.log_worker_initiated()

    def log_worker_initiated(self):
        LOG.info("Processor worker ID [%s] is initiated as CloudKitty "
                 "rating processor.", self._worker_id)

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
            self.internal_run()

    def terminate(self):
        LOG.debug('Terminating worker {}.'.format(self._worker_id))
        self.coord.stop()
        LOG.debug('Terminated worker {}.'.format(self._worker_id))

    def internal_run(self):
        self.load_scopes_to_process()
        for tenant_id in self.tenants:
            lock_name, lock = get_lock(
                self.coord, self.generate_lock_base_name(tenant_id))

            LOG.debug('[Worker: {w}] Trying to acquire lock "{lock_name}" for '
                      'scope ID {scope_id}.'.format(w=self._worker_id,
                                                    lock_name=lock_name,
                                                    scope_id=tenant_id))

            lock_acquired = lock.acquire(blocking=False)
            if lock_acquired:
                LOG.debug('[Worker: {w}] Acquired lock "{lock_name}" for '
                          'scope ID {scope_id}.'.format(w=self._worker_id,
                                                        lock_name=lock_name,
                                                        scope_id=tenant_id))

                try:
                    self.process_scope(tenant_id)
                finally:
                    lock.release()

                LOG.debug("Finished processing scope [%s].", tenant_id)
            else:
                LOG.debug("Could not acquire lock [%s] for processing "
                          "scope [%s] with worker [%s].", lock_name,
                          tenant_id, self.worker_class)
        LOG.debug("Finished processing all storage scopes with worker "
                  "[worker_id=%s, class=%s].",
                  self._worker_id, self.worker_class)
        # FIXME(sheeprine): We may cause a drift here
        time.sleep(CONF.collect.period)

    def process_scope(self, scope_to_process):
        timestamp = self.next_timestamp_to_process(scope_to_process)
        LOG.debug("Next timestamp [%s] found for processing for "
                  "storage scope [%s].", state, scope_to_process)

        if not timestamp:
            LOG.debug("There is no next timestamp to process for scope [%s]",
                      scope_to_process)
            return

        worker = self.worker_class(
            self.collector,
            self.storage,
            scope_to_process,
            self._worker_id,
        )
        worker.run()

    def generate_lock_base_name(self, tenant_id):
        return tenant_id

    def load_scopes_to_process(self):
        self.tenants = self.fetcher.get_tenants()
        random.shuffle(self.tenants)

        LOG.info('[Worker: {w}] Tenants loaded for fetcher {f}'.format(
            w=self._worker_id, f=self.fetcher.name))


class CloudKittyReprocessor(CloudKittyProcessor):
    def __init__(self, worker_id):
        super(CloudKittyReprocessor, self).__init__(worker_id)

        self.next_timestamp_to_process = self._next_timestamp_to_process
        self.worker_class = ReprocessingWorker

        self.reprocessing_scheduler_db = state.ReprocessingSchedulerDb()

    def log_worker_initiated(self):
        LOG.info("Processor worker ID [%s] is initiated as CloudKitty "
                 "rating reprocessor.", self._worker_id)

    def _next_timestamp_to_process(self, scope):
        scope_db = self.reprocessing_scheduler_db.get_from_db(
            identifier=scope.identifier,
            start_reprocess_time=scope.start_reprocess_time,
            end_reprocess_time=scope.end_reprocess_time)

        if scope_db:
            return ReprocessingWorker.generate_next_timestamp(
                scope_db, CONF.collect.period)
        else:
            LOG.debug("It seems that the processing for schedule [%s] was "
                      "finished by other CloudKitty reprocessor.", scope)
            return None

    def load_scopes_to_process(self):
        self.tenants = self.reprocessing_scheduler_db.get_all()
        random.shuffle(self.tenants)

        LOG.info('Reprocessing worker [%s] loaded [%s] schedules to process.',
                 self._worker_id, len(self.tenants))

    def generate_lock_base_name(self, scope):
        return "%s-id=%s-start=%s-end=%s" % (self.worker_class,
                                             scope.identifier,
                                             scope.start_reprocess_time,
                                             scope.end_reprocess_time)


class CloudKittyServiceManager(cotyledon.ServiceManager):

    def __init__(self):
        super(CloudKittyServiceManager, self).__init__()
        if CONF.orchestrator.max_workers:
            self.cloudkitty_processor_service_id = self.add(
                CloudKittyProcessor, workers=CONF.orchestrator.max_workers)
        else:
            LOG.info("No worker configured for CloudKitty processing.")

        if CONF.orchestrator.max_workers_reprocessing:
            self.cloudkitty_reprocessor_service_id = self.add(
                CloudKittyReprocessor,
                workers=CONF.orchestrator.max_workers_reprocessing)
        else:
            LOG.info("No worker configured for CloudKitty reprocessing.")
