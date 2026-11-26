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
from oslo_utils import timeutils

from cloudkitty import state
from cloudkitty import tests


class DBStateManagerTest(tests.TestCase):
    def setUp(self):
        super(DBStateManagerTest, self).setUp()
        self.sm = state.DBStateManager('testuser', 'osrtf')

    def test_gen_name(self):
        name = self.sm._gen_name('testuser', 'osrtf')
        self.assertEqual('testuser_osrtf', name)

    def test_state_access(self):
        now = timeutils.utcnow()
        self.sm.set_state(now)
        result = self.sm.get_state()
        self.assertEqual(str(now), result)

    def test_metadata_access(self):
        metadata = {'foo': 'bar'}
        now = timeutils.utcnow()
        self.sm.set_state(now)
        self.sm.set_metadata(metadata)
        result = self.sm.get_metadata()
        self.assertEqual(metadata, result)

    def test_metadata_access_select_one(self):
        sm_alt = state.DBStateManager('testuser_alt', 'osrtf')
        now = timeutils.utcnow()

        metadata = {'foo': 'bar'}
        self.sm.set_state(now)
        self.sm.set_metadata(metadata)

        metadata_alt = {'baz': 'qux'}
        sm_alt.set_state(now)
        sm_alt.set_metadata(metadata_alt)
        sm_alt.set_metadata(metadata_alt)

        self.assertEqual(metadata, self.sm.get_metadata())
        self.assertEqual(metadata_alt, sm_alt.get_metadata())
