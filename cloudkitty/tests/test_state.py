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
# @author: Gauvain Pocentek
#
import datetime
import testtools

from cloudkitty import state
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class DBStateManagerTest(tests.TestCase):
    def setUp(self):
        super(DBStateManagerTest, self).setUp()
        self.sm = state.DBStateManager('testuser', 'osrtf')

    def test_gen_name(self):
        name = self.sm._gen_name('testuser', 'osrtf')
        self.assertEqual(name, 'testuser_osrtf')

    def test_state_access(self):
        now = datetime.datetime.utcnow()
        self.sm.set_state(now)
        result = self.sm.get_state()
        self.assertEqual(result, str(now))

    def test_metadata_access(self):
        metadata = {'foo': 'bar'}
        now = datetime.datetime.utcnow()
        self.sm.set_state(now)
        self.sm.set_metadata(metadata)
        result = self.sm.get_metadata()
        self.assertEqual(result, metadata)
