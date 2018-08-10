# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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

from cloudkitty.db import api as ck_db_api
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test


class FakeRPCClient(object):
    def __init__(self, namespace=None, fanout=False):
        self._queue = []
        self._namespace = namespace
        self._fanout = fanout

    def prepare(self, namespace=None, fanout=False):
        self._namespace = namespace
        self._fanout = fanout
        return self

    def cast(self, ctx, data, **kwargs):
        cast_data = {'ctx': ctx,
                     'data': data}
        cast_data.update(kwargs)
        self._queue.append(cast_data)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class RatingTest(tests.TestCase):
    def setUp(self):
        super(RatingTest, self).setUp()
        self._tenant_id = 'f266f30b11f246b589fd266f85eeec39'
        self._module = tests.FakeRatingModule(self._tenant_id)
        self._fake_rpc = FakeRPCClient()

    def test_get_module_info(self):
        mod_infos = self._module.module_info
        expected_infos = {'name': 'fake',
                          'description': 'fake rating module',
                          'hot_config': False,
                          'enabled': False,
                          'priority': 1}
        self.assertEqual(expected_infos, mod_infos)

    def test_set_state_triggers_rpc(self):
        with mock.patch('cloudkitty.messaging.get_client') as rpcmock:
            rpcmock.return_value = self._fake_rpc
            self._module.set_state(True)
            self.assertTrue(self._fake_rpc._fanout)
            self.assertEqual('rating', self._fake_rpc._namespace)
            self.assertEqual(1, len(self._fake_rpc._queue))
            rpc_data = self._fake_rpc._queue[0]
            expected_data = {'ctx': {},
                             'data': 'enable_module',
                             'name': 'fake'}
            self.assertEqual(expected_data, rpc_data)
            self._module.set_state(False)
            self.assertEqual(2, len(self._fake_rpc._queue))
            rpc_data = self._fake_rpc._queue[1]
            expected_data['data'] = 'disable_module'
            self.assertEqual(expected_data, rpc_data)

    def test_enable_module(self):
        with mock.patch('cloudkitty.messaging.get_client') as rpcmock:
            rpcmock.return_value = self._fake_rpc
            self._module.set_state(True)
        db_api = ck_db_api.get_instance()
        module_db = db_api.get_module_info()
        self.assertTrue(module_db.get_state('fake'))

    def test_disable_module(self):
        with mock.patch('cloudkitty.messaging.get_client') as rpcmock:
            rpcmock.return_value = self._fake_rpc
            self._module.set_state(False)
        db_api = ck_db_api.get_instance()
        module_db = db_api.get_module_info()
        self.assertFalse(module_db.get_state('fake'))

    def test_enabled_property(self):
        db_api = ck_db_api.get_instance()
        module_db = db_api.get_module_info()
        module_db.set_state('fake', True)
        self.assertTrue(self._module.enabled)
        module_db.set_state('fake', False)
        self.assertFalse(self._module.enabled)

    def test_get_default_priority(self):
        self.assertEqual(1, self._module.priority)

    def test_set_priority(self):
        self._module.set_priority(10)
        db_api = ck_db_api.get_instance()
        module_db = db_api.get_module_info()
        self.assertEqual(10, module_db.get_priority('fake'))

    def test_update_priority(self):
        old_prio = self._module.priority
        self._module.set_priority(10)
        new_prio = self._module.priority
        self.assertNotEqual(old_prio, new_prio)
