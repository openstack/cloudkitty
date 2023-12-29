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
import datetime
import re

from unittest import mock

from oslo_messaging import conffixture
from stevedore import extension
from tooz import coordination
from tooz.drivers import file

from cloudkitty import collector
from cloudkitty import orchestrator
from cloudkitty.storage.v2 import influx
from cloudkitty import storage_state
from cloudkitty import tests
from cloudkitty.utils import tz as tzutils


class FakeKeystoneClient(object):

    class FakeTenants(object):
        def list(self):
            return ['f266f30b11f246b589fd266f85eeec39',
                    '4dfb25b0947c4f5481daf7b948c14187']

    tenants = FakeTenants()


class ScopeEndpointTest(tests.TestCase):
    def setUp(self):
        super(ScopeEndpointTest, self).setUp()
        messaging_conf = self.useFixture(conffixture.ConfFixture(self.conf))
        messaging_conf.transport_url = 'fake:/'
        self.conf.set_override('backend', 'influxdb', 'storage')

    def test_reset_state(self):
        coord_start_patch = mock.patch.object(
            coordination.CoordinationDriverWithExecutor, 'start')
        lock_acquire_patch = mock.patch.object(
            file.FileLock, 'acquire', return_value=True)

        storage_delete_patch = mock.patch.object(
            influx.InfluxStorage, 'delete')

        state_set_patch = mock.patch.object(
            storage_state.StateManager, 'set_last_processed_timestamp')

        with coord_start_patch, lock_acquire_patch, \
                storage_delete_patch as sd, state_set_patch as ss:

            endpoint = orchestrator.ScopeEndpoint()
            endpoint.reset_state({}, {
                'scopes': [
                    {
                        'scope_id': 'f266f30b11f246b589fd266f85eeec39',
                        'scope_key': 'project_id',
                        'collector': 'prometheus',
                        'fetcher': 'prometheus',
                    },
                    {
                        'scope_id': '4dfb25b0947c4f5481daf7b948c14187',
                        'scope_key': 'project_id',
                        'collector': 'gnocchi',
                        'fetcher': 'gnocchi',
                    },
                ],
                'last_processed_timestamp': '20190716T085501Z',
            })

            sd.assert_has_calls([
                mock.call(
                    begin=tzutils.utc_to_local(
                        datetime.datetime(2019, 7, 16, 8, 55, 1)),
                    end=None,
                    filters={'project_id': 'f266f30b11f246b589fd266f85eeec39'}
                ),
                mock.call(
                    begin=tzutils.utc_to_local(
                        datetime.datetime(2019, 7, 16, 8, 55, 1)),
                    end=None,
                    filters={'project_id': '4dfb25b0947c4f5481daf7b948c14187'},
                )
            ], any_order=True)

            ss.assert_has_calls([
                mock.call(
                    'f266f30b11f246b589fd266f85eeec39',
                    tzutils.utc_to_local(
                        datetime.datetime(2019, 7, 16, 8, 55, 1)),
                    scope_key='project_id',
                    collector='prometheus',
                    fetcher='prometheus'),
                mock.call(
                    '4dfb25b0947c4f5481daf7b948c14187',
                    tzutils.utc_to_local(
                        datetime.datetime(2019, 7, 16, 8, 55, 1)),
                    scope_key='project_id',
                    collector='gnocchi',
                    fetcher='gnocchi')], any_order=True)


class OrchestratorTest(tests.TestCase):
    def setUp(self):
        super(OrchestratorTest, self).setUp()
        messaging_conf = self.useFixture(conffixture.ConfFixture(self.conf))
        messaging_conf.transport_url = 'fake:/'
        self.conf.set_override('backend', 'keystone', 'fetcher')
        self.conf.import_group('fetcher_keystone',
                               'cloudkitty.fetcher.keystone')

    def setup_fake_modules(self):
        fake_module1 = tests.FakeRatingModule()
        fake_module1.module_name = 'fake1'
        fake_module1.set_priority(3)
        fake_module2 = tests.FakeRatingModule()
        fake_module2.module_name = 'fake2'
        fake_module2.set_priority(1)
        fake_module3 = tests.FakeRatingModule()
        fake_module3.module_name = 'fake3'
        fake_module3.set_priority(2)
        fake_extensions = [
            extension.Extension(
                'fake1',
                'cloudkitty.tests.FakeRatingModule1',
                None,
                fake_module1),
            extension.Extension(
                'fake2',
                'cloudkitty.tests.FakeRatingModule2',
                None,
                fake_module2),
            extension.Extension(
                'fake3',
                'cloudkitty.tests.FakeRatingModule3',
                None,
                fake_module3)]
        return fake_extensions

    def test_processors_ordering_in_workers(self):
        fake_extensions = self.setup_fake_modules()
        ck_ext_mgr = 'cloudkitty.extension_manager.EnabledExtensionManager'
        with mock.patch(ck_ext_mgr) as stevemock:
            fake_mgr = extension.ExtensionManager.make_test_instance(
                fake_extensions,
                'cloudkitty.rating.processors')
            stevemock.return_value = fake_mgr
            worker = orchestrator.BaseWorker()
            stevemock.assert_called_once_with(
                'cloudkitty.rating.processors',
                invoke_kwds={'tenant_id': None})
            self.assertEqual('fake1', worker._processors[0].name)
            self.assertEqual(3, worker._processors[0].obj.priority)
            self.assertEqual('fake3', worker._processors[1].name)
            self.assertEqual(2, worker._processors[1].obj.priority)
            self.assertEqual('fake2', worker._processors[2].name)
            self.assertEqual(1, worker._processors[2].obj.priority)

    @mock.patch("cotyledon.ServiceManager.add")
    @mock.patch("cotyledon._service_manager.ServiceManager.__init__")
    def test_cloudkitty_service_manager_only_processing(
            self, service_manager_init_mock, cotyledon_add_mock):

        OrchestratorTest.execute_cloudkitty_service_manager_test(
            cotyledon_add_mock=cotyledon_add_mock, max_workers_reprocessing=0,
            max_workers=1)

        self.assertTrue(service_manager_init_mock.called)

    @mock.patch("cotyledon.ServiceManager.add")
    @mock.patch("cotyledon._service_manager.ServiceManager.__init__")
    def test_cloudkitty_service_manager_only_reprocessing(
            self, service_manager_init_mock, cotyledon_add_mock):
        OrchestratorTest.execute_cloudkitty_service_manager_test(
            cotyledon_add_mock=cotyledon_add_mock, max_workers_reprocessing=1,
            max_workers=0)

        self.assertTrue(service_manager_init_mock.called)

    @mock.patch("cotyledon.ServiceManager.add")
    @mock.patch("cotyledon._service_manager.ServiceManager.__init__")
    def test_cloudkitty_service_manager_both_processings(
            self, service_manager_init_mock, cotyledon_add_mock):
        OrchestratorTest.execute_cloudkitty_service_manager_test(
            cotyledon_add_mock=cotyledon_add_mock)

        self.assertTrue(service_manager_init_mock.called)

    @staticmethod
    def execute_cloudkitty_service_manager_test(cotyledon_add_mock=None,
                                                max_workers=1,
                                                max_workers_reprocessing=1):

        original_conf = orchestrator.CONF
        try:
            orchestrator.CONF = mock.Mock()
            orchestrator.CONF.orchestrator = mock.Mock()
            orchestrator.CONF.orchestrator.max_workers = max_workers
            orchestrator.CONF.orchestrator.max_workers_reprocessing = \
                max_workers_reprocessing

            orchestrator.CloudKittyServiceManager()

            expected_calls = []
            if max_workers:
                expected_calls.append(
                    mock.call(orchestrator.CloudKittyProcessor,
                              workers=max_workers))

            if max_workers_reprocessing:
                expected_calls.append(
                    mock.call(orchestrator.CloudKittyReprocessor,
                              workers=max_workers_reprocessing))

            cotyledon_add_mock.assert_has_calls(expected_calls)
        finally:
            orchestrator.CONF = original_conf


class WorkerTest(tests.TestCase):

    def setUp(self):
        super(WorkerTest, self).setUp()

        patcher_state_manager_set_state = mock.patch(
            "cloudkitty.storage_state.StateManager.set_state")
        self.addCleanup(patcher_state_manager_set_state.stop)
        self.state_manager_set_state_mock = \
            patcher_state_manager_set_state.start()

        self._tenant_id = 'a'
        self._worker_id = '0'

        self.collector_mock = mock.MagicMock()
        self.storage_mock = mock.MagicMock()
        self.collector_mock.__str__.return_value = "toString"

        load_conf_manager = mock.patch("cloudkitty.utils.load_conf")
        self.addCleanup(load_conf_manager.stop)
        self.load_conf_mock = load_conf_manager.start()

        self.worker = orchestrator.Worker(self.collector_mock,
                                          self.storage_mock, self._tenant_id,
                                          self._worker_id)

    def test_do_collection_all_valid(self):
        timestamp_now = tzutils.localized_now()

        metrics = ['metric{}'.format(i) for i in range(5)]
        side_effect = [(
            metrics[i],
            {'period': {'begin': 0,
                        'end': 3600},
             'usage': i},
        ) for i in range(5)]
        self.collector_mock.retrieve.side_effect = side_effect
        output = sorted(self.worker._do_collection(metrics,
                                                   timestamp_now).items(),
                        key=lambda x: x[1]['usage'])
        self.assertEqual(side_effect, output)

    def test_do_collection_some_empty(self):
        timestamp_now = tzutils.localized_now()

        metrics = ['metric{}'.format(i) for i in range(7)]
        side_effect = [(
            metrics[i],
            {'period': {'begin': 0,
                        'end': 3600},
             'usage': i},
        ) for i in range(5)]
        side_effect.insert(2, collector.NoDataCollected('a', 'b'))
        side_effect.insert(4, collector.NoDataCollected('a', 'b'))
        self.collector_mock.retrieve.side_effect = side_effect
        output = sorted(self.worker._do_collection(
            metrics, timestamp_now).items(),
                        key=lambda x: x[1]['usage'])
        self.assertEqual([
            i for i in side_effect
            if not isinstance(i, collector.NoDataCollected)
        ], output)

    def test_update_scope_processing_state_db(self):
        timestamp = tzutils.localized_now()
        self.worker.update_scope_processing_state_db(timestamp)

        self.state_manager_set_state_mock.assert_has_calls([
            mock.call(self.worker._tenant_id, timestamp)
        ])

    @mock.patch("cloudkitty.dataframe.DataFrame")
    def test_execute_measurements_rating(self, dataframe_mock):
        new_data_frame_mock = mock.Mock()

        dataframe_mock.return_value = new_data_frame_mock
        processor_mock_1 = mock.Mock()

        return_processor_1 = mock.Mock()
        processor_mock_1.obj.process.return_value = return_processor_1

        processor_mock_2 = mock.Mock()
        return_processor_2 = mock.Mock()
        processor_mock_2.obj.process.return_value = return_processor_2

        self.worker._processors = [processor_mock_1, processor_mock_2]

        start_time = tzutils.localized_now()
        end_time = start_time + datetime.timedelta(hours=1)
        return_of_method = self.worker.execute_measurements_rating(
            end_time, start_time, {})

        self.assertEqual(return_processor_2, return_of_method)

        processor_mock_1.obj.process.assert_has_calls([
            mock.call(new_data_frame_mock)
        ])
        processor_mock_2.obj.process.assert_has_calls([
            mock.call(return_processor_1)
        ])
        dataframe_mock.assert_has_calls([
            mock.call(start=start_time, end=end_time, usage={})
        ])

    def test_persist_rating_data(self):
        start_time = tzutils.localized_now()
        end_time = start_time + datetime.timedelta(hours=1)

        frame = {"id": "sd"}
        self.worker.persist_rating_data(end_time, frame, start_time)

        self.storage_mock.push.assert_has_calls([
            mock.call([frame], self.worker._tenant_id)
        ])

    @mock.patch("cloudkitty.orchestrator.Worker._do_collection")
    @mock.patch("cloudkitty.orchestrator.Worker.execute_measurements_rating")
    @mock.patch("cloudkitty.orchestrator.Worker.persist_rating_data")
    @mock.patch("cloudkitty.orchestrator.Worker"
                ".update_scope_processing_state_db")
    def test_do_execute_scope_processing_with_no_usage_data(
            self, update_scope_processing_state_db_mock,
            persist_rating_data_mock, execute_measurements_rating_mock,
            do_collection_mock):
        self.worker._collector = collector.gnocchi.GnocchiCollector(
            period=3600,
            conf=tests.samples.DEFAULT_METRICS_CONF,
        )
        do_collection_mock.return_value = None

        timestamp_now = tzutils.localized_now()
        self.worker.do_execute_scope_processing(timestamp_now)

        do_collection_mock.assert_has_calls([
            mock.call(['cpu@#instance', 'image.size', 'ip.floating',
                       'network.incoming.bytes', 'network.outgoing.bytes',
                       'radosgw.objects.size', 'volume.size'], timestamp_now)
        ])

        self.assertFalse(execute_measurements_rating_mock.called)
        self.assertFalse(persist_rating_data_mock.called)
        self.assertTrue(update_scope_processing_state_db_mock.called)

    @mock.patch("cloudkitty.orchestrator.Worker._do_collection")
    @mock.patch("cloudkitty.orchestrator.Worker.execute_measurements_rating")
    @mock.patch("cloudkitty.orchestrator.Worker.persist_rating_data")
    @mock.patch("cloudkitty.orchestrator.Worker"
                ".update_scope_processing_state_db")
    def test_do_execute_scope_processing_with_usage_data(
            self, update_scope_processing_state_db_mock,
            persist_rating_data_mock, execute_measurements_rating_mock,
            do_collection_mock):
        self.worker._collector = collector.gnocchi.GnocchiCollector(
            period=3600,
            conf=tests.samples.DEFAULT_METRICS_CONF,
        )

        usage_data_mock = {"some_usage_data": 2}
        do_collection_mock.return_value = usage_data_mock

        execute_measurements_rating_mock_return = mock.Mock()
        execute_measurements_rating_mock.return_value =\
            execute_measurements_rating_mock_return

        timestamp_now = tzutils.localized_now()
        self.worker.do_execute_scope_processing(timestamp_now)

        do_collection_mock.assert_has_calls([
            mock.call(['cpu@#instance', 'image.size', 'ip.floating',
                       'network.incoming.bytes', 'network.outgoing.bytes',
                       'radosgw.objects.size', 'volume.size'], timestamp_now)
        ])

        end_time = tzutils.add_delta(
            timestamp_now, datetime.timedelta(seconds=self.worker._period))
        execute_measurements_rating_mock.assert_has_calls([
            mock.call(end_time, timestamp_now, usage_data_mock)
        ])

        persist_rating_data_mock.assert_has_calls([
            mock.call(end_time, execute_measurements_rating_mock_return,
                      timestamp_now)
        ])
        self.assertTrue(update_scope_processing_state_db_mock.called)

    @mock.patch("cloudkitty.storage_state.StateManager"
                ".get_last_processed_timestamp")
    @mock.patch("cloudkitty.storage_state.StateManager"
                ".is_storage_scope_active")
    @mock.patch("cloudkitty.orchestrator.Worker.do_execute_scope_processing")
    def test_execute_worker_processing_no_next_timestamp(
            self, do_execute_scope_processing_mock,
            state_manager_is_storage_scope_active_mock,
            state_manager_get_stage_mock):

        next_timestamp_to_process_mock = mock.Mock()
        next_timestamp_to_process_mock.return_value = None

        self.worker.next_timestamp_to_process = next_timestamp_to_process_mock

        return_method_value = self.worker.execute_worker_processing()

        self.assertFalse(return_method_value)
        self.assertFalse(state_manager_get_stage_mock.called)
        self.assertFalse(state_manager_is_storage_scope_active_mock.called)
        self.assertFalse(do_execute_scope_processing_mock.called)
        self.assertTrue(next_timestamp_to_process_mock.called)

    @mock.patch("cloudkitty.storage_state.StateManager"
                ".get_last_processed_timestamp")
    @mock.patch("cloudkitty.storage_state.StateManager"
                ".is_storage_scope_active")
    @mock.patch("cloudkitty.orchestrator.Worker.do_execute_scope_processing")
    def test_execute_worker_processing_scope_not_processed_yet(
            self, do_execute_scope_processing_mock,
            state_manager_is_storage_scope_active_mock,
            state_manager_get_stage_mock):

        timestamp_now = tzutils.localized_now()
        next_timestamp_to_process_mock = mock.Mock()
        next_timestamp_to_process_mock.return_value = timestamp_now

        self.worker.next_timestamp_to_process = next_timestamp_to_process_mock

        state_manager_get_stage_mock.return_value = None
        return_method_value = self.worker.execute_worker_processing()

        self.assertTrue(return_method_value)

        state_manager_get_stage_mock.assert_has_calls([
            mock.call(self.worker._tenant_id)
        ])

        do_execute_scope_processing_mock.assert_has_calls([
            mock.call(timestamp_now)
        ])
        self.assertFalse(state_manager_is_storage_scope_active_mock.called)
        self.assertTrue(next_timestamp_to_process_mock.called)

    @mock.patch("cloudkitty.storage_state.StateManager"
                ".get_last_processed_timestamp")
    @mock.patch("cloudkitty.storage_state.StateManager"
                ".is_storage_scope_active")
    @mock.patch("cloudkitty.orchestrator.Worker.do_execute_scope_processing")
    def test_execute_worker_processing_scope_already_processed_active(
            self, do_execute_scope_processing_mock,
            state_manager_is_storage_scope_active_mock,
            state_manager_get_stage_mock):

        timestamp_now = tzutils.localized_now()
        next_timestamp_to_process_mock = mock.Mock()
        next_timestamp_to_process_mock.return_value = timestamp_now

        self.worker.next_timestamp_to_process = next_timestamp_to_process_mock

        state_manager_get_stage_mock.return_value = mock.Mock()
        state_manager_is_storage_scope_active_mock.return_value = True

        return_method_value = self.worker.execute_worker_processing()

        self.assertTrue(return_method_value)

        state_manager_get_stage_mock.assert_has_calls([
            mock.call(self.worker._tenant_id)
        ])

        do_execute_scope_processing_mock.assert_has_calls([
            mock.call(timestamp_now)
        ])
        state_manager_is_storage_scope_active_mock.assert_has_calls([
            mock.call(self.worker._tenant_id)
        ])

        self.assertTrue(next_timestamp_to_process_mock.called)

    @mock.patch("cloudkitty.storage_state.StateManager"
                ".get_last_processed_timestamp")
    @mock.patch("cloudkitty.storage_state.StateManager"
                ".is_storage_scope_active")
    @mock.patch("cloudkitty.orchestrator.Worker.do_execute_scope_processing")
    def test_execute_worker_processing_scope_already_processed_inactive(
            self, do_execute_scope_processing_mock,
            state_manager_is_storage_scope_active_mock,
            state_manager_get_stage_mock):

        timestamp_now = tzutils.localized_now()
        next_timestamp_to_process_mock = mock.Mock()
        next_timestamp_to_process_mock.return_value = timestamp_now

        self.worker.next_timestamp_to_process = next_timestamp_to_process_mock

        state_manager_get_stage_mock.return_value = mock.Mock()
        state_manager_is_storage_scope_active_mock.return_value = False

        return_method_value = self.worker.execute_worker_processing()

        self.assertFalse(return_method_value)

        state_manager_get_stage_mock.assert_has_calls([
            mock.call(self.worker._tenant_id)
        ])

        state_manager_is_storage_scope_active_mock.assert_has_calls([
            mock.call(self.worker._tenant_id)
        ])

        self.assertTrue(next_timestamp_to_process_mock.called)
        self.assertFalse(do_execute_scope_processing_mock.called)

    @mock.patch("cloudkitty.orchestrator.Worker.execute_worker_processing")
    def test_run(self, execute_worker_processing_mock):
        execute_worker_processing_mock.side_effect = [True, True, False, True]

        self.worker.run()

        self.assertEqual(execute_worker_processing_mock.call_count, 3)

    def test_collect_no_data(self):
        metric = "metric1"
        timestamp_now = tzutils.localized_now()

        self.collector_mock.retrieve.return_value = (metric, None)

        expected_message = "Collector 'toString' returned no data for " \
                           "resource 'metric1'"
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(
            collector.NoDataCollected, expected_message, self.worker._collect,
            metric, timestamp_now)

        next_timestamp = tzutils.add_delta(
            timestamp_now, datetime.timedelta(seconds=self.worker._period))

        self.collector_mock.retrieve.assert_has_calls([
            mock.call(metric, timestamp_now, next_timestamp,
                      self.worker._tenant_id)])

    def test_collect_with_data(self):
        metric = "metric1"
        timestamp_now = tzutils.localized_now()

        usage_data = {"some_usage_data": 3}
        self.collector_mock.retrieve.return_value = (metric, usage_data)

        return_of_method = self.worker._collect(metric, timestamp_now)

        next_timestamp = tzutils.add_delta(
            timestamp_now, datetime.timedelta(seconds=self.worker._period))

        self.collector_mock.retrieve.assert_has_calls([
            mock.call(metric, timestamp_now, next_timestamp,
                      self.worker._tenant_id)])

        self.assertEqual((metric, usage_data), return_of_method)

    @mock.patch("cloudkitty.utils.check_time_state")
    def test_check_state(self, check_time_state_mock):
        state_mock = mock.Mock()

        timestamp_now = tzutils.localized_now()
        state_mock._state.get_last_processed_timestamp.return_value = \
            timestamp_now

        expected_time = timestamp_now + datetime.timedelta(hours=1)
        check_time_state_mock.return_value = \
            expected_time

        return_of_method = orchestrator._check_state(
            state_mock, 3600, self._tenant_id)

        self.assertEqual(expected_time, return_of_method)

        state_mock._state.get_last_processed_timestamp.assert_has_calls([
            mock.call(self._tenant_id)])
        check_time_state_mock.assert_has_calls([
            mock.call(timestamp_now, 3600, 2)])


class CloudKittyReprocessorTest(tests.TestCase):

    def setUp(self):
        super(CloudKittyReprocessorTest, self).setUp()

    @mock.patch("cloudkitty.orchestrator.CloudKittyProcessor.__init__")
    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb")
    def test_generate_lock_base_name(self, reprocessing_scheduler_db_mock,
                                     cloudkitty_processor_init_mock):

        scope_mock = mock.Mock()
        scope_mock.identifier = "scope_identifier"

        return_generate_lock_name = orchestrator.CloudKittyReprocessor(
            1).generate_lock_base_name(scope_mock)

        expected_lock_name = "<class 'cloudkitty.orchestrator." \
                             "ReprocessingWorker'>-id=scope_identifier-" \
                             "start=%s-end=%s" % (
                                 scope_mock.start_reprocess_time,
                                 scope_mock.end_reprocess_time)

        self.assertEqual(expected_lock_name, return_generate_lock_name)

        cloudkitty_processor_init_mock.assert_called_once()
        reprocessing_scheduler_db_mock.assert_called_once()

    @mock.patch("cloudkitty.orchestrator.CloudKittyProcessor.__init__")
    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb.get_all")
    def test_load_scopes_to_process(self, scheduler_db_mock_get_all_mock,
                                    cloudkitty_processor_init_mock):
        scheduler_db_mock_get_all_mock.return_value = ["teste"]

        reprocessor = CloudKittyReprocessorTest.create_cloudkitty_reprocessor()
        reprocessor.load_scopes_to_process()

        self.assertEqual(["teste"], reprocessor.tenants)
        cloudkitty_processor_init_mock.assert_called_once()
        scheduler_db_mock_get_all_mock.assert_called_once()

    @mock.patch("cloudkitty.orchestrator.CloudKittyProcessor.__init__")
    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb.get_from_db")
    def test_next_timestamp_to_process_processing_finished(
            self, scheduler_db_mock_get_from_db_mock,
            cloudkitty_processor_init_mock):

        start_time = tzutils.localized_now()

        scope = CloudKittyReprocessorTest.create_scope_mock(start_time)

        scheduler_db_mock_get_from_db_mock.return_value = None

        reprocessor = CloudKittyReprocessorTest.create_cloudkitty_reprocessor()

        next_timestamp = reprocessor._next_timestamp_to_process(scope)

        expected_calls = [
            mock.call(identifier=scope.identifier,
                      start_reprocess_time=scope.start_reprocess_time,
                      end_reprocess_time=scope.end_reprocess_time)]

        self.assertIsNone(next_timestamp)
        cloudkitty_processor_init_mock.assert_called_once()
        scheduler_db_mock_get_from_db_mock.assert_has_calls(expected_calls)

    @staticmethod
    def create_scope_mock(start_time):
        scope = mock.Mock()
        scope.identifier = "scope_identifier"
        scope.start_reprocess_time = start_time
        scope.current_reprocess_time = None
        scope.end_reprocess_time = start_time + datetime.timedelta(hours=1)
        return scope

    @staticmethod
    def create_cloudkitty_reprocessor():
        reprocessor = orchestrator.CloudKittyReprocessor(1)
        reprocessor._worker_id = 1

        return reprocessor

    @mock.patch("cloudkitty.orchestrator.CloudKittyProcessor.__init__")
    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb.get_from_db")
    def test_next_timestamp_to_process(
            self, scheduler_db_mock_get_from_db_mock,
            cloudkitty_processor_init_mock):

        start_time = tzutils.localized_now()

        scope = CloudKittyReprocessorTest.create_scope_mock(start_time)

        scheduler_db_mock_get_from_db_mock.return_value = scope

        reprocessor = CloudKittyReprocessorTest.create_cloudkitty_reprocessor()

        next_timestamp = reprocessor._next_timestamp_to_process(scope)

        expected_calls = [
            mock.call(identifier=scope.identifier,
                      start_reprocess_time=scope.start_reprocess_time,
                      end_reprocess_time=scope.end_reprocess_time)]

        # There is no current timestamp in the mock object.
        # Therefore, the next to process is the start timestamp
        expected_next_timestamp = start_time
        self.assertEqual(expected_next_timestamp, next_timestamp)
        cloudkitty_processor_init_mock.assert_called_once()
        scheduler_db_mock_get_from_db_mock.assert_has_calls(expected_calls)


class CloudKittyProcessorTest(tests.TestCase):

    def setUp(self):
        super(CloudKittyProcessorTest, self).setUp()

        patcher_oslo_messaging_target = mock.patch("oslo_messaging.Target")
        self.addCleanup(patcher_oslo_messaging_target.stop)
        self.oslo_messaging_target_mock = patcher_oslo_messaging_target.start()

        patcher_messaging_get_server = mock.patch(
            "cloudkitty.messaging.get_server")

        self.addCleanup(patcher_messaging_get_server.stop)
        self.messaging_get_server_mock = patcher_messaging_get_server.start()

        patcher_driver_manager = mock.patch("stevedore.driver.DriverManager")
        self.addCleanup(patcher_driver_manager.stop)
        self.driver_manager_mock = patcher_driver_manager.start()

        get_collector_manager = mock.patch(
            "cloudkitty.collector.get_collector")
        self.addCleanup(get_collector_manager.stop)
        self.get_collector_mock = get_collector_manager.start()

        self.worker_id = 1
        self.cloudkitty_processor = orchestrator.CloudKittyProcessor(
            self.worker_id)

    def test_init_messaging(self):
        server_mock = mock.Mock()
        self.messaging_get_server_mock.return_value = server_mock

        target_object_mock = mock.Mock()
        self.oslo_messaging_target_mock.return_value = target_object_mock

        self.cloudkitty_processor._init_messaging()

        server_mock.start.assert_called_once()
        self.oslo_messaging_target_mock.assert_has_calls([
            mock.call(topic='cloudkitty', server=orchestrator.CONF.host,
                      version='1.0')])

        self.messaging_get_server_mock.assert_has_calls([
            mock.call(target_object_mock, [
                self.cloudkitty_processor._rating_endpoint,
                self.cloudkitty_processor._scope_endpoint])])

    @mock.patch("time.sleep")
    @mock.patch("cloudkitty.orchestrator.CloudKittyProcessor."
                "load_scopes_to_process")
    @mock.patch("cloudkitty.orchestrator.CloudKittyProcessor."
                "process_scope")
    @mock.patch("cloudkitty.orchestrator.get_lock")
    def test_internal_run(self, get_lock_mock, process_scope_mock,
                          load_scopes_to_process_mock, sleep_mock):

        lock_mock = mock.Mock()
        lock_mock.acquire.return_value = True
        get_lock_mock.return_value = ("lock_name", lock_mock)

        self.cloudkitty_processor.tenants = ["tenant1"]

        self.cloudkitty_processor.internal_run()

        lock_mock.acquire.assert_has_calls([mock.call(blocking=False)])
        lock_mock.release.assert_called_once()

        get_lock_mock.assert_has_calls(
            [mock.call(self.cloudkitty_processor.coord, "tenant1")])

        sleep_mock.assert_called_once()
        process_scope_mock.assert_called_once()
        load_scopes_to_process_mock.assert_called_once()

    @mock.patch("cloudkitty.orchestrator.Worker")
    def test_process_scope_no_next_timestamp(self, worker_class_mock):

        original_next_timestamp_method = \
            self.cloudkitty_processor.next_timestamp_to_process
        next_timestamp_mock_method = mock.Mock()
        try:
            self.cloudkitty_processor.next_timestamp_to_process =\
                next_timestamp_mock_method

            scope_mock = mock.Mock()
            next_timestamp_mock_method.return_value = None

            self.cloudkitty_processor.process_scope(scope_mock)

            next_timestamp_mock_method.assert_has_calls(
                [mock.call(scope_mock)])
            self.assertFalse(worker_class_mock.called)
        finally:
            self.cloudkitty_processor.next_timestamp_to_process =\
                original_next_timestamp_method

    @mock.patch("cloudkitty.orchestrator.Worker")
    def test_process_scope(self, worker_class_mock):
        original_next_timestamp_method =\
            self.cloudkitty_processor.next_timestamp_to_process
        next_timestamp_mock_method = mock.Mock()

        worker_mock = mock.Mock()
        worker_class_mock.return_value = worker_mock

        original_worker_class = self.cloudkitty_processor.worker_class
        self.cloudkitty_processor.worker_class = worker_class_mock

        try:
            self.cloudkitty_processor.next_timestamp_to_process =\
                next_timestamp_mock_method

            scope_mock = mock.Mock()
            next_timestamp_mock_method.return_value = tzutils.localized_now()

            self.cloudkitty_processor.process_scope(scope_mock)

            next_timestamp_mock_method.assert_has_calls(
                [mock.call(scope_mock)])
            worker_class_mock.assert_has_calls(
                [mock.call(self.cloudkitty_processor.collector,
                           self.cloudkitty_processor.storage, scope_mock,
                           self.cloudkitty_processor._worker_id)])

            worker_mock.run.assert_called_once()
        finally:
            self.cloudkitty_processor.next_timestamp_to_process =\
                original_next_timestamp_method
            self.cloudkitty_processor.worker_class = original_worker_class

    def test_generate_lock_base_name(self):
        generated_lock_name = self.cloudkitty_processor.\
            generate_lock_base_name("scope_id")

        self.assertEqual("scope_id", generated_lock_name)

    def test_load_scopes_to_process(self):
        fetcher_mock = mock.Mock()
        self.cloudkitty_processor.fetcher = fetcher_mock

        fetcher_mock.get_tenants.return_value = ["scope_1"]

        self.cloudkitty_processor.load_scopes_to_process()

        fetcher_mock.get_tenants.assert_called_once()
        self.assertEqual(["scope_1"], self.cloudkitty_processor.tenants)

    def test_terminate(self):
        coordinator_mock = mock.Mock()
        self.cloudkitty_processor.coord = coordinator_mock

        self.cloudkitty_processor.terminate()

        coordinator_mock.stop.assert_called_once()


class ReprocessingWorkerTest(tests.TestCase):

    def setUp(self):
        super(ReprocessingWorkerTest, self).setUp()

        patcher_reprocessing_scheduler_db_get_from_db = mock.patch(
            "cloudkitty.storage_state.ReprocessingSchedulerDb.get_from_db")
        self.addCleanup(patcher_reprocessing_scheduler_db_get_from_db.stop)
        self.reprocessing_scheduler_db_get_from_db_mock =\
            patcher_reprocessing_scheduler_db_get_from_db.start()

        patcher_state_manager_get_all = mock.patch(
            "cloudkitty.storage_state.StateManager.get_all")
        self.addCleanup(patcher_state_manager_get_all.stop)
        self.state_manager_get_all_mock = patcher_state_manager_get_all.start()

        self.collector_mock = mock.Mock()
        self.storage_mock = mock.Mock()

        self.scope_key_mock = "key_mock"
        self.worker_id = 1
        self.scope_id = "scope_id1"
        self.scope_mock = mock.Mock()
        self.scope_mock.identifier = self.scope_id

        load_conf_manager = mock.patch("cloudkitty.utils.load_conf")
        self.addCleanup(load_conf_manager.stop)
        self.load_conf_mock = load_conf_manager.start()

        def to_string_scope_mock(self):
            return "toStringMock"
        self.scope_mock.__str__ = to_string_scope_mock
        self.scope_mock.scope_key = self.scope_key_mock

        self.state_manager_get_all_mock.return_value = [self.scope_mock]

        self.reprocessing_worker = self.create_reprocessing_worker()

        self.mock_scheduler = mock.Mock()
        self.mock_scheduler.identifier = self.scope_id

        self.start_schedule_mock = tzutils.localized_now()
        self.mock_scheduler.start_reprocess_time = self.start_schedule_mock
        self.mock_scheduler.current_reprocess_time = None
        self.mock_scheduler.end_reprocess_time =\
            self.start_schedule_mock + datetime.timedelta(hours=1)

    def create_reprocessing_worker(self):
        return orchestrator.ReprocessingWorker(
            self.collector_mock, self.storage_mock, self.scope_mock,
            self.worker_id)

    def test_load_scope_key_scope_not_found(self):
        self.state_manager_get_all_mock.return_value = []

        expected_message = "Scope [toStringMock] scheduled for reprocessing " \
                           "does not seem to exist anymore."
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(Exception, expected_message,
                               self.reprocessing_worker.load_scope_key)

        self.state_manager_get_all_mock.assert_has_calls([
            mock.call(self.reprocessing_worker._tenant_id)])

    def test_load_scope_key_more_than_one_scope_found(self):
        self.state_manager_get_all_mock.return_value = [
            self.scope_mock, self.scope_mock]

        expected_message = "Unexpected number of storage state entries " \
                           "found for scope [toStringMock]."
        expected_message = re.escape(expected_message)

        self.assertRaisesRegex(Exception, expected_message,
                               self.reprocessing_worker.load_scope_key)

        self.state_manager_get_all_mock.assert_has_calls([
            mock.call(self.reprocessing_worker._tenant_id)])

    def test_load_scope_key(self):
        self.reprocessing_worker.load_scope_key()

        self.state_manager_get_all_mock.assert_has_calls([
            mock.call(self.reprocessing_worker._tenant_id)])

        self.assertEqual(self.scope_key_mock,
                         self.reprocessing_worker.scope_key)

    @mock.patch("cloudkitty.orchestrator.ReprocessingWorker"
                ".generate_next_timestamp")
    def test_next_timestamp_to_process_no_db_item(
            self, generate_next_timestamp_mock):

        self.reprocessing_scheduler_db_get_from_db_mock.return_value = []

        self.reprocessing_worker._next_timestamp_to_process()

        self.reprocessing_scheduler_db_get_from_db_mock.assert_has_calls([
            mock.call(
                identifier=self.scope_mock.identifier,
                start_reprocess_time=self.scope_mock.start_reprocess_time,
                end_reprocess_time=self.scope_mock.end_reprocess_time)])

        self.assertFalse(generate_next_timestamp_mock.called)

    @mock.patch("cloudkitty.orchestrator.ReprocessingWorker"
                ".generate_next_timestamp")
    def test_next_timestamp_to_process(self, generate_next_timestamp_mock):
        self.reprocessing_scheduler_db_get_from_db_mock.\
            return_value = self.scope_mock

        self.reprocessing_worker._next_timestamp_to_process()

        self.reprocessing_scheduler_db_get_from_db_mock.assert_has_calls([
            mock.call(
                identifier=self.scope_mock.identifier,
                start_reprocess_time=self.scope_mock.start_reprocess_time,
                end_reprocess_time=self.scope_mock.end_reprocess_time)])

        generate_next_timestamp_mock.assert_has_calls([
            mock.call(self.scope_mock, self.reprocessing_worker._period)])

    def test_generate_next_timestamp_no_current_processing(self):
        next_timestamp = self.reprocessing_worker.generate_next_timestamp(
            self.mock_scheduler, 300)

        self.assertEqual(self.start_schedule_mock, next_timestamp)

        self.mock_scheduler.start_reprocess_time += datetime.timedelta(hours=2)

        next_timestamp = self.reprocessing_worker.generate_next_timestamp(
            self.mock_scheduler, 300)

        self.assertIsNone(next_timestamp)

    def test_generate_next_timestamp_with_current_processing(self):
        period = 300

        self.mock_scheduler.current_reprocess_time =\
            self.start_schedule_mock + datetime.timedelta(seconds=period)

        expected_next_time_stamp =\
            self.mock_scheduler.current_reprocess_time + datetime.timedelta(
                seconds=period)

        next_timestamp = self.reprocessing_worker.generate_next_timestamp(
            self.mock_scheduler, period)

        self.assertEqual(expected_next_time_stamp, next_timestamp)

        self.mock_scheduler.current_reprocess_time +=\
            datetime.timedelta(hours=2)

        next_timestamp = self.reprocessing_worker.generate_next_timestamp(
            self.mock_scheduler, period)

        self.assertIsNone(next_timestamp)

    @mock.patch("cloudkitty.orchestrator.Worker.do_execute_scope_processing")
    def test_do_execute_scope_processing(
            self, do_execute_scope_processing_mock_from_worker):

        now_timestamp = tzutils.localized_now()
        self.reprocessing_worker.scope.start_reprocess_time = now_timestamp
        self.reprocessing_worker.do_execute_scope_processing(now_timestamp)

        self.storage_mock.delete.assert_has_calls([
            mock.call(
                begin=self.reprocessing_worker.scope.start_reprocess_time,
                end=self.reprocessing_worker.scope.end_reprocess_time,
                filters={
                    self.reprocessing_worker.scope_key:
                        self.reprocessing_worker._tenant_id})])

        do_execute_scope_processing_mock_from_worker.assert_has_calls([
            mock.call(now_timestamp)])

    @mock.patch("cloudkitty.storage_state.ReprocessingSchedulerDb"
                ".update_reprocessing_time")
    def test_update_scope_processing_state_db(
            self, update_reprocessing_time_mock):

        timestamp_now = tzutils.localized_now()
        self.reprocessing_worker.update_scope_processing_state_db(
            timestamp_now)

        start_time = self.reprocessing_worker.scope.start_reprocess_time
        end_time = self.reprocessing_worker.scope.end_reprocess_time
        update_reprocessing_time_mock.assert_has_calls([
            mock.call(
                identifier=self.reprocessing_worker.scope.identifier,
                start_reprocess_time=start_time, end_reprocess_time=end_time,
                new_current_time_stamp=timestamp_now)])
