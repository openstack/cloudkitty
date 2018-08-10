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
import testtools

import mock
import testscenarios

from cloudkitty import storage
from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty.tests import test_utils
from cloudkitty.tests.utils import is_functional_test
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

    @mock.patch('cloudkitty.storage.v1.hybrid.backends.gnocchi.gclient')
    @mock.patch('cloudkitty.utils.load_conf', new=test_utils.load_conf)
    def setUp(self, gclient_mock):
        super(StorageTest, self).setUp()
        self._tenant_id = samples.TENANT
        self._other_tenant_id = '8d3ae50089ea4142-9c6e1269db6a0b64'
        self.conf.set_override('backend', self.storage_backend, 'storage')
        self.conf.set_override('version', '1', 'storage')
        self.storage = storage.get_storage(conf=test_utils.load_conf())
        self.storage.init()

    def insert_data(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.push(working_data, self._tenant_id)
        working_data = copy.deepcopy(samples.RATED_DATA)
        self.storage.push(working_data, self._other_tenant_id)

    def insert_different_data_two_tenants(self):
        working_data = copy.deepcopy(samples.RATED_DATA)
        del working_data[1]
        self.storage.push(working_data, self._tenant_id)
        working_data = copy.deepcopy(samples.RATED_DATA)
        del working_data[0]
        self.storage.push(working_data, self._other_tenant_id)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class StorageDataframeTest(StorageTest):

    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy'))]

    # Queries
    # Data
    def test_get_no_frame_when_nothing_in_storage(self):
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.retrieve,
            begin=samples.FIRST_PERIOD_BEGIN - 3600,
            end=samples.FIRST_PERIOD_BEGIN)

    def test_get_frame_filter_outside_data(self):
        self.insert_different_data_two_tenants()
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.retrieve,
            begin=samples.FIRST_PERIOD_BEGIN - 3600,
            end=samples.FIRST_PERIOD_BEGIN)

    def test_get_frame_without_filter_but_timestamp(self):
        self.insert_different_data_two_tenants()
        data = self.storage.retrieve(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.SECOND_PERIOD_END)['dataframes']
        self.assertEqual(3, len(data))

    def test_get_frame_on_one_period(self):
        self.insert_different_data_two_tenants()
        data = self.storage.retrieve(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.FIRST_PERIOD_END)['dataframes']
        self.assertEqual(2, len(data))

    def test_get_frame_on_one_period_and_one_tenant(self):
        self.insert_different_data_two_tenants()
        group_filters = {'project_id': self._tenant_id}
        data = self.storage.retrieve(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.FIRST_PERIOD_END,
            group_filters=group_filters)['dataframes']
        self.assertEqual(2, len(data))

    def test_get_frame_on_one_period_and_one_tenant_outside_data(self):
        self.insert_different_data_two_tenants()
        group_filters = {'project_id': self._other_tenant_id}
        self.assertRaises(
            storage.NoTimeFrame,
            self.storage.retrieve,
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.FIRST_PERIOD_END,
            group_filters=group_filters)

    def test_get_frame_on_two_periods(self):
        self.insert_different_data_two_tenants()
        data = self.storage.retrieve(
            begin=samples.FIRST_PERIOD_BEGIN,
            end=samples.SECOND_PERIOD_END)['dataframes']
        self.assertEqual(3, len(data))


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class StorageTotalTest(StorageTest):

    storage_scenarios = [
        ('sqlalchemy', dict(storage_backend='sqlalchemy'))]

    # Total
    def test_get_empty_total(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN - 3600)
        end = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        self.insert_data()
        total = self.storage.total(
            begin=begin,
            end=end)
        self.assertEqual(1, len(total))
        self.assertEqual(total[0]["rate"], 0)
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_without_filter_but_timestamp(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.total(
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
        total = self.storage.total(
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
        group_filters = {'project_id': self._tenant_id}
        total = self.storage.total(
            begin=begin,
            end=end,
            group_filters=group_filters)
        self.assertEqual(1, len(total))
        self.assertEqual(0.5537, total[0]["rate"])
        self.assertEqual(self._tenant_id, total[0]["tenant_id"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_filtering_on_service(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.FIRST_PERIOD_END)
        self.insert_data()
        total = self.storage.total(
            begin=begin,
            end=end,
            metric_types='instance')
        self.assertEqual(1, len(total))
        self.assertEqual(0.84, total[0]["rate"])
        self.assertEqual('instance', total[0]["res_type"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])

    def test_get_total_groupby_tenant(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.total(
            begin=begin,
            end=end,
            groupby=['project_id'])
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
        total = self.storage.total(
            begin=begin,
            end=end,
            groupby=['type'])
        self.assertEqual(2, len(total))
        self.assertEqual(0.2674, total[0]["rate"])
        self.assertEqual('image.size', total[0]["res_type"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])
        self.assertEqual(1.68, total[1]["rate"])
        self.assertEqual('instance', total[1]["res_type"])
        self.assertEqual(begin, total[1]["begin"])
        self.assertEqual(end, total[1]["end"])

    def test_get_total_groupby_tenant_and_restype(self):
        begin = ck_utils.ts2dt(samples.FIRST_PERIOD_BEGIN)
        end = ck_utils.ts2dt(samples.SECOND_PERIOD_END)
        self.insert_data()
        total = self.storage.total(
            begin=begin,
            end=end,
            groupby=['project_id', 'type'])
        self.assertEqual(4, len(total))
        self.assertEqual(0.1337, total[0]["rate"])
        self.assertEqual(self._other_tenant_id, total[0]["tenant_id"])
        self.assertEqual('image.size', total[0]["res_type"])
        self.assertEqual(begin, total[0]["begin"])
        self.assertEqual(end, total[0]["end"])
        self.assertEqual(0.1337, total[1]["rate"])
        self.assertEqual(self._tenant_id, total[1]["tenant_id"])
        self.assertEqual('image.size', total[1]["res_type"])
        self.assertEqual(begin, total[1]["begin"])
        self.assertEqual(end, total[1]["end"])
        self.assertEqual(0.84, total[2]["rate"])
        self.assertEqual(self._other_tenant_id, total[2]["tenant_id"])
        self.assertEqual('instance', total[2]["res_type"])
        self.assertEqual(begin, total[2]["begin"])
        self.assertEqual(end, total[2]["end"])
        self.assertEqual(0.84, total[3]["rate"])
        self.assertEqual(self._tenant_id, total[3]["tenant_id"])
        self.assertEqual('instance', total[3]["res_type"])
        self.assertEqual(begin, total[3]["begin"])
        self.assertEqual(end, total[3]["end"])


if not is_functional_test():
    StorageTest.generate_scenarios()
    StorageTotalTest.generate_scenarios()
    StorageDataframeTest.generate_scenarios()
