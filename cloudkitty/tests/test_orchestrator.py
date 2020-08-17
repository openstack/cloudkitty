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
            storage_state.StateManager, 'set_state')

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
                'state': '20190716T085501Z',
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


class WorkerTest(tests.TestCase):

    def setUp(self):
        super(WorkerTest, self).setUp()

        class FakeWorker(orchestrator.Worker):
            def __init__(self):
                self._tenant_id = 'a'
                self._worker_id = '0'
                self._log_prefix = '[IGNORE THIS MESSAGE]'

        self.worker = FakeWorker()
        self.worker._collect = mock.MagicMock()

    def test_do_collection_all_valid(self):
        metrics = ['metric{}'.format(i) for i in range(5)]
        side_effect = [(
            metrics[i],
            {'period': {'begin': 0,
                        'end': 3600},
             'usage': i},
        ) for i in range(5)]
        self.worker._collect.side_effect = side_effect
        output = sorted(self.worker._do_collection(metrics, 0).items(),
                        key=lambda x: x[1]['usage'])
        self.assertEqual(side_effect, output)

    def test_do_collection_some_empty(self):
        metrics = ['metric{}'.format(i) for i in range(7)]
        side_effect = [(
            metrics[i],
            {'period': {'begin': 0,
                        'end': 3600},
             'usage': i},
        ) for i in range(5)]
        side_effect.insert(2, collector.NoDataCollected('a', 'b'))
        side_effect.insert(4, collector.NoDataCollected('a', 'b'))
        self.worker._collect.side_effect = side_effect
        output = sorted(self.worker._do_collection(metrics, 0).items(),
                        key=lambda x: x[1]['usage'])
        self.assertEqual([
            i for i in side_effect
            if not isinstance(i, collector.NoDataCollected)
        ], output)
