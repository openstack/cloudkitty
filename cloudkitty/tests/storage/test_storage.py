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
import copy

import mock
import sqlalchemy
import testscenarios

from cloudkitty import storage
from cloudkitty.storage.hybrid.backends import gnocchi as hgnocchi
from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty import utils as ck_utils


class StorageTest(tests.TestCase):
    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy')),
        ('hybrid', dict(storage_backend='hybrid'))]

    @classmethod
    def generate_scenarios(cls):
        cls.scenarios = testscenarios.multiply_scenarios(
            cls.scenarios,
            cls.storage_scenarios)

    @mock.patch('cloudkitty.storage.hybrid.backends.gnocchi.gclient')
    def setUp(self, gclient_mock):
        super(StorageTest, self).setUp()
        hgnocchi.METRICS_CONF = samples.METRICS_CONF
        self._tenant_id = samples.TENANT
        self._other_tenant_id = '8d3ae50089ea4142-9c6e1269db6a0b64'
        self.conf.set_override('backend', self.storage_backend, 'storage')
        self.storage = storage.get_storage()
        self.storage.init()

    def insert_data(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append(working_data, self._tenant_id)
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append(working_data, self._other_tenant_id)
        self.storage.commit(self._tenant_id)
        self.storage.commit(self._other_tenant_id)

    def insert_different_data_two_tenants(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        del working_data[1]
        self.storage.append(working_data, self._tenant_id)
        working_data = copy.deepcopy(samples.RATED_DATA)
        del working_data[0]
        self.storage.append(working_data, self._other_tenant_id)
        self.storage.commit(self._tenant_id)
        self.storage.commit(self._other_tenant_id)

    # Filtering
    def test_filter_period(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        usage_start, data = self.storage._filter_period(working_data)
        self.assertEqual(samples.FIRST_PERIOD_BEGIN, usage_start)
        self.assertEqual(samples.RATED_DATA[0]['usage'], data)
        expected_remaining_data = [{
            "period": samples.SECOND_PERIOD,
            "usage": samples.RATED_DATA[1]['usage']}]
        self.assertEqual(expected_remaining_data, working_data)
        usage_start, data = self.storage._filter_period(working_data)
        self.assertEqual(samples.SECOND_PERIOD_BEGIN, usage_start)
        self.assertEqual(samples.RATED_DATA[1]['usage'], data)
        self.assertEqual([], working_data)

    # State
    def test_get_state_when_nothing_in_storage(self):
        state = self.storage.get_state()
        self.assertIsNone(state)

    def test_get_latest_global_state(self):
        self.insert_different_data_two_tenants()
        state = self.storage.get_state()
        self.assertEqual(samples.SECOND_PERIOD_BEGIN, state)

    def test_get_state_on_rated_tenant(self):
        self.insert_different_data_two_tenants()
        state = self.storage.get_state(self._tenant_id)
        self.assertEqual(samples.FIRST_PERIOD_BEGIN, state)
        state = self.storage.get_state(self._other_tenant_id)
        self.assertEqual(samples.SECOND_PERIOD_BEGIN, state)

    def test_get_state_on_no_data_frame(self):
        self.storage.nodata(
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id)
        self.storage.commit(self._tenant_id)
        state = self.storage.get_state(self._tenant_id)
        self.assertEqual(samples.FIRST_PERIOD_BEGIN, state)


class StorageDataframeTest(StorageTest):

    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy'))]

    # Queries
    # Data
    def test_get_no_frame_when_nothing_in_storage(self):
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.get_time_frame,
            begin=samples.FIRST_PERIOD_BEGIN - 3600,
            end=samples.FIRST_PERIOD_BEGIN)

    def test_get_frame_filter_outside_data(self):
        self.insert_different_data_two_tenants()
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.get_time_frame,
            begin=samples.FIRST_PERIOD_BEGIN - 3600,
            end=samples.FIRST_PERIOD_BEGIN)

    def test_get_frame_without_filter_but_timestamp(self):
        self.insert_different_data_two_tenants()
        data = self.storage.get_time_frame(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.SECOND_PERIOD_END)
        self.assertEqual(3, len(data))

    def test_get_frame_on_one_period(self):
        self.insert_different_data_two_tenants()
        data = self.storage.get_time_frame(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.FIRST_PERIOD_END)
        self.assertEqual(2, len(data))

    def test_get_frame_on_one_period_and_one_tenant(self):
        self.insert_different_data_two_tenants()
        data = self.storage.get_time_frame(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.FIRST_PERIOD_END,
            tenant_id=self._tenant_id)
        self.assertEqual(2, len(data))

    def test_get_frame_on_one_period_and_one_tenant_outside_data(self):
        self.insert_different_data_two_tenants()
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.get_time_frame,
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.FIRST_PERIOD_END,
            tenant_id=self._other_tenant_id)

    def test_get_frame_on_two_periods(self):
        self.insert_different_data_two_tenants()
        data = self.storage.get_time_frame(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.SECOND_PERIOD_END)
        self.assertEqual(3, len(data))


class StorageTotalTest(StorageTest):

    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy'))]

    # Total
    def test_get_empty_total(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN - 3600)
        end = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end)
        self.assertEqual(1, len(total))
        self.assertIsNone(total[0]["rate"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_without_filter_but_timestamp(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end)
        # FIXME(sheeprine): floating point error (transition to decimal)
        self.assertEqual(1, len(total))
        self.assertEqual(1.9473999999999998, total[0]["rate"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_filtering_on_one_period(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.FIRST_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end)
        self.assertEqual(1, len(total))
        self.assertEqual(1.1074, total[0]["rate"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_filtering_on_one_period_and_one_tenant(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.FIRST_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end,
            tenant_id=self._tenant_id)
        self.assertEqual(1, len(total))
        self.assertEqual(0.5537, total[0]["rate"])
        self.assertEqual(self._tenant_id, total[0]["tenant_id"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_filtering_on_service(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.FIRST_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end,
            service='compute')
        self.assertEqual(1, len(total))
        self.assertEqual(0.84, total[0]["rate"])
        self.assertEqual('compute', total[0]["res_type"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_groupby_tenant(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end,
            groupby="tenant_id")
        self.assertEqual(2, len(total))
        self.assertEqual(0.9737, total[0]["rate"])
        self.assertEqual(self._other_tenant_id, total[0]["tenant_id"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])
        self.assertEqual(0.9737, total[1]["rate"])
        self.assertEqual(self._tenant_id, total[1]["tenant_id"])
        self.assertEqual(begin, total[1]["begin"])
        self.assertEqual(end, total[1]["end"])

    def test_get_total_groupby_restype(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end,
            groupby="res_type")
        self.assertEqual(2, len(total))
        self.assertEqual(0.2674, total[0]["rate"])
        self.assertEqual('image', total[0]["res_type"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])
        self.assertEqual(1.68, total[1]["rate"])
        self.assertEqual('compute', total[1]["res_type"])
        self.assertEqual(begin, total[1]["begin"])
        self.assertEqual(end, total[1]["end"])

    def test_get_total_groupby_tenant_and_restype(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.get_total(
            begin=begin,
            end=end,
            groupby="tenant_id,res_type")
        self.assertEqual(4, len(total))
        self.assertEqual(0.1337, total[0]["rate"])
        self.assertEqual(self._other_tenant_id, total[0]["tenant_id"])
        self.assertEqual('image', total[0]["res_type"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])
        self.assertEqual(0.1337, total[1]["rate"])
        self.assertEqual(self._tenant_id, total[1]["tenant_id"])
        self.assertEqual('image', total[1]["res_type"])
        self.assertEqual(begin, total[1]["begin"])
        self.assertEqual(end, total[1]["end"])
        self.assertEqual(0.84, total[2]["rate"])
        self.assertEqual(self._other_tenant_id, total[2]["tenant_id"])
        self.assertEqual('compute', total[2]["res_type"])
        self.assertEqual(begin, total[2]["begin"])
        self.assertEqual(end, total[2]["end"])
        self.assertEqual(0.84, total[3]["rate"])
        self.assertEqual(self._tenant_id, total[3]["tenant_id"])
        self.assertEqual('compute', total[3]["res_type"])
        self.assertEqual(begin, total[3]["begin"])
        self.assertEqual(end, total[3]["end"])


class StorageTenantTest(StorageTest):

    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy'))]

    # Tenants
    def test_get_empty_tenant_with_nothing_in_storage(self):
        tenants = self.storage.get_tenants(
            begin=ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN),
            end=ck_utils.ts2dt(samples.SECOND_PERIOD_BEGIN))
        self.assertEqual([], tenants)

    def test_get_empty_tenant_list(self):
        self.insert_data()
        tenants = self.storage.get_tenants(
            begin=ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN - 3600),
            end=ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN))
        self.assertEqual([], tenants)

    def test_get_tenants_filtering_on_period(self):
        self.insert_different_data_two_tenants()
        tenants = self.storage.get_tenants(
            begin=ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN),
            end=ck_utils.ts2dt(samples.SECOND_PERIOD_END))
        self.assertListEqual(
            [self._tenant_id, self._other_tenant_id],
            tenants)
        tenants = self.storage.get_tenants(
            begin=ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN),
            end=ck_utils.ts2dt(samples.FIRST_PERIOD_END))
        self.assertListEqual(
            [self._tenant_id],
            tenants)
        tenants = self.storage.get_tenants(
            begin=ck_utils.ts2dt(samples.SECOND_PERIOD_BEGIN),
            end=ck_utils.ts2dt(samples.SECOND_PERIOD_END))
        self.assertListEqual(
            [self._other_tenant_id],
            tenants)


class StorageDataIntegrityTest(StorageTest):

    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy'))]

    # Data integrity
    def test_has_data_flag_behaviour(self):
        self.assertNotIn(self._tenant_id, self.storage._has_data)
        self.storage.nodata(
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id)
        self.assertNotIn(self._tenant_id, self.storage._has_data)
        working_data = copy.deepcopy(samples.RATED_DATA)
        working_data = [working_data[1]]
        self.storage.append(working_data, self._tenant_id)
        self.assertTrue(self.storage._has_data[self._tenant_id])
        self.storage.commit(self._tenant_id)
        self.assertNotIn(self._tenant_id, self.storage._has_data)

    def test_notify_no_data(self):
        self.storage.nodata(
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id)
        working_data = copy.deepcopy(samples.RATED_DATA)
        working_data = [working_data[1]]
        self.storage.append(working_data, self._tenant_id)
        kwargs = {
            'begin': samples.FIRST_PERIOD_BEGIN,
            'end': samples.FIRST_PERIOD_END,
            'tenant_id': self._tenant_id}
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.get_time_frame,
            **kwargs)
        kwargs['res_type'] = '_NO_DATA_'
        stored_data = self.storage.get_time_frame(**kwargs)
        self.assertEqual(1, len(stored_data))
        self.assertEqual(1, len(stored_data[0]['usage']))
        self.assertIn('_NO_DATA_', stored_data[0]['usage'])

    def test_send_nodata_between_data(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        for period in working_data:
            for service, data in sorted(period['usage'].items()):
                sub_data = [{
                    'period': period['period'],
                    'usage': {
                        service: data}}]
                self.storage.append(sub_data, self._tenant_id)
                if service == 'compute':
                    self.storage.nodata(
                        period['period']['begin'],
                        period['period']['end'],
                        self._tenant_id)
            self.storage.commit(self._tenant_id)
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.get_time_frame,
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.SECOND_PERIOD_END,
            res_type='_NO_DATA_')

    def test_auto_commit_on_period_change(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append(working_data, self._tenant_id)
        stored_data = self.storage.get_time_frame(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.SECOND_PERIOD_END)
        self.assertEqual(2, len(stored_data))
        expected_data = copy.deepcopy(samples.STORED_DATA)
        # We only stored the first timeframe, the second one is waiting for a
        # commit or an append with the next timeframe.
        del expected_data[2]
        # NOTE(sheeprine): Quick and dirty sort (ensure result consistency,
        # order is not significant to the test result)
        if 'image' in stored_data[0]['usage']:
            stored_data[0]['usage'], stored_data[1]['usage'] = (
                stored_data[1]['usage'], stored_data[0]['usage'])
        self.assertEqual(
            expected_data,
            stored_data)

    def test_create_session_on_append(self):
        self.assertNotIn(self._tenant_id, self.storage._session)
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append(working_data, self._tenant_id)
        self.assertIn(self._tenant_id, self.storage._session)
        self.assertIsInstance(
            self.storage._session[self._tenant_id],
            sqlalchemy.orm.session.Session)

    def test_delete_session_on_commit(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append(working_data, self._tenant_id)
        self.storage.commit(self._tenant_id)
        self.assertNotIn(self._tenant_id, self.storage._session)

    def test_update_period_on_append(self):
        self.assertNotIn(self._tenant_id, self.storage.usage_start)
        self.assertNotIn(self._tenant_id, self.storage.usage_start_dt)
        self.assertNotIn(self._tenant_id, self.storage.usage_end)
        self.assertNotIn(self._tenant_id, self.storage.usage_end_dt)
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append([working_data[0]], self._tenant_id)
        self.assertEqual(
            self.storage.usage_start[self._tenant_id],
            samples.FIRST_PERIOD_BEGIN)
        self.assertEqual(
            self.storage.usage_start_dt[self._tenant_id],
            ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN))
        self.assertEqual(
            self.storage.usage_end[self._tenant_id],
            samples.FIRST_PERIOD_END)
        self.assertEqual(
            self.storage.usage_end_dt[self._tenant_id],
            ck_utils.ts2dt(samples.FIRST_PERIOD_END))
        self.storage.append([working_data[1]], self._tenant_id)
        self.assertEqual(
            self.storage.usage_start[self._tenant_id],
            samples.SECOND_PERIOD_BEGIN)
        self.assertEqual(
            self.storage.usage_start_dt[self._tenant_id],
            ck_utils.ts2dt(samples.SECOND_PERIOD_BEGIN))
        self.assertEqual(
            self.storage.usage_end[self._tenant_id],
            samples.SECOND_PERIOD_END)
        self.assertEqual(
            self.storage.usage_end_dt[self._tenant_id],
            ck_utils.ts2dt(samples.SECOND_PERIOD_END))

    def test_clear_period_info_on_commit(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.append(working_data, self._tenant_id)
        self.storage.commit(self._tenant_id)
        self.assertNotIn(self._tenant_id, self.storage.usage_start)
        self.assertNotIn(self._tenant_id, self.storage.usage_start_dt)
        self.assertNotIn(self._tenant_id, self.storage.usage_end)
        self.assertNotIn(self._tenant_id, self.storage.usage_end_dt)


StorageTest.generate_scenarios()
StorageTotalTest.generate_scenarios()
StorageTenantTest.generate_scenarios()
StorageDataframeTest.generate_scenarios()
StorageDataIntegrityTest.generate_scenarios()
