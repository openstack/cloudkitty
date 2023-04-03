# -*- coding: utf-8 -*-
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
#
from unittest import mock

from cloudkitty.fetcher import gnocchi
from cloudkitty import tests


class GnocchiFetcherTest(tests.TestCase):

    def setUp(self):
        super(GnocchiFetcherTest, self).setUp()

        self.fetcher = gnocchi.GnocchiFetcher()

        self.resource_list = [{'id': "some_id",
                               'project_id': 'some_other_project_id'},
                              {'id': "some_id2",
                               'project_id': 'some_other_project_id2'},
                              {'id': "some_id3",
                               'project_id': 'some_other_project_id3'},
                              {'id': "some_replicated_id",
                               'project_id': 'some_replicated_id_project'},
                              {'id': "some_replicated_id",
                               'project_id': 'some_replicated_id_project'}
                              ]
        self.unique_scope_ids = ["some_other_project_id",
                                 "some_other_project_id2",
                                 "some_other_project_id3",
                                 "some_replicated_id_project"]

        self.unique_scope_ids.sort()

    def test_get_tenants_marker_list_resource_last_call(self):
        with mock.patch.object(
                self.fetcher._conn.resource, 'search') as resource_list:
            resource_list.side_effect = [
                self.resource_list,
                [{'id': "some_replicated_id",
                  'project_id': 'some_replicated_id_project'}], []]

            all_scope_ids = self.fetcher.get_tenants()
            all_scope_ids.sort()

            self.assertEqual(self.unique_scope_ids, all_scope_ids)

            resource_list.assert_has_calls([
                mock.call(resource_type='generic', details=True, query=None),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}}),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}})
            ])

    def test_get_tenants_empty_list_resource_last_call(self):
        with mock.patch.object(
                self.fetcher._conn.resource, 'search') as resource_list:
            resource_list.side_effect = [
                self.resource_list, self.resource_list, []]

            all_scope_ids = self.fetcher.get_tenants()
            all_scope_ids.sort()

            self.assertEqual(self.unique_scope_ids, all_scope_ids)

            resource_list.assert_has_calls([
                mock.call(resource_type='generic', details=True, query=None),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}}),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}})],
                any_order=False)

    def test_get_tenants_scope_id_as_none(self):
        with mock.patch.object(
                self.fetcher._conn.resource, 'search') as resource_list:
            resource_list.side_effect = [
                self.resource_list, self.resource_list,
                [{"id": "test", "project_id": None}], []]

            all_scope_ids = self.fetcher.get_tenants()
            all_scope_ids.sort()

            self.assertEqual(self.unique_scope_ids, all_scope_ids)

            resource_list.assert_has_calls([
                mock.call(resource_type='generic', details=True, query=None),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}}),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}}),
                mock.call(resource_type='generic', details=True,
                          query={'not': {'in': {'project_id': [
                              'some_other_project_id',
                              'some_other_project_id2',
                              'some_other_project_id3',
                              'some_replicated_id_project']}}})
            ], any_order=False)
