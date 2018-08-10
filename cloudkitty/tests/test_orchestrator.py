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
import testtools

import mock
from oslo_messaging import conffixture
from stevedore import extension

from cloudkitty import orchestrator
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test


class FakeKeystoneClient(object):

    class FakeTenants(object):
        def list(self):
            return ['f266f30b11f246b589fd266f85eeec39',
                    '4dfb25b0947c4f5481daf7b948c14187']

    tenants = FakeTenants()


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class OrchestratorTest(tests.TestCase):
    def setUp(self):
        super(OrchestratorTest, self).setUp()
        messaging_conf = self.useFixture(conffixture.ConfFixture(self.conf))
        messaging_conf.transport_url = 'fake:/'
        self.conf.set_override('backend', 'keystone', 'fetcher')
        self.conf.import_group('keystone_fetcher',
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
