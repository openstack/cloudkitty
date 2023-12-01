# Copyright 2018 Objectif Libre
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

import testscenarios
from werkzeug import exceptions as http_exceptions

from cloudkitty import storage

from cloudkitty.tests import samples
from cloudkitty.tests.storage.v2 import es_utils
from cloudkitty.tests.storage.v2 import influx_utils
from cloudkitty.tests.storage.v2 import opensearch_utils
from cloudkitty.tests import TestCase
from cloudkitty.tests import utils as test_utils
from cloudkitty.utils import tz as tzutils


_ES_CLIENT_PATH = ('cloudkitty.storage.v2.elasticsearch'
                   '.client.ElasticsearchClient')

_INFLUX_CLIENT_PATH = 'cloudkitty.storage.v2.influx.InfluxClient'


_OS_CLIENT_PATH = ('cloudkitty.storage.v2.opensearch'
                   '.client.OpenSearchClient')


class StorageUnitTest(TestCase):

    storage_scenarios = [
        ('influxdb', dict(storage_backend='influxdb')),
        ('elasticsearch', dict(storage_backend='elasticsearch')),
        ('opensearch', dict(storage_backend='opensearch'))]

    @classmethod
    def generate_scenarios(cls):
        cls.scenarios = testscenarios.multiply_scenarios(
            cls.scenarios,
            cls.storage_scenarios)

    @mock.patch(_ES_CLIENT_PATH,
                new=es_utils.FakeElasticsearchClient)
    @mock.patch(_INFLUX_CLIENT_PATH,
                new=influx_utils.FakeInfluxClient)
    @mock.patch(_OS_CLIENT_PATH,
                new=opensearch_utils.FakeOpenSearchClient)
    @mock.patch('cloudkitty.utils.load_conf', new=test_utils.load_conf)
    def setUp(self):
        super(StorageUnitTest, self).setUp()
        self._project_id = samples.TENANT
        self._other_project_id = samples.OTHER_TENANT
        self.conf.set_override('backend', self.storage_backend, 'storage')
        self.conf.set_override('version', '2', 'storage')
        self.storage = storage.get_storage(conf=test_utils.load_conf())
        self.storage.init()
        self.data = []
        self.init_data()

    def init_data(self):
        project_ids = [self._project_id, self._other_project_id]
        start_base = tzutils.utc_to_local(datetime.datetime(2018, 1, 1))
        for i in range(3):
            start_delta = datetime.timedelta(seconds=3600 * i)
            end_delta = start_delta + datetime.timedelta(seconds=3600)
            start = tzutils.add_delta(start_base, start_delta)
            end = tzutils.add_delta(start_base, end_delta)
            data = test_utils.generate_v2_storage_data(
                project_ids=project_ids,
                start=start,
                end=end)
            self.data.append(data)
            self.storage.push([data])

    @staticmethod
    def _expected_total_qty_len(data, project_id=None, types=None):
        total = 0
        qty = 0
        length = 0
        for dataframe in data:
            for mtype, points in dataframe.itertypes():
                if types is not None and mtype not in types:
                    continue
                for point in points:
                    if project_id is None or \
                       project_id == point.groupby['project_id']:
                        total += point.price
                        qty += point.qty
                        length += 1

        return round(float(total), 5), round(float(qty), 5), length

    def _compare_get_total_result_with_expected(self,
                                                expected_qty,
                                                expected_total,
                                                expected_total_len,
                                                total):
        self.assertEqual(len(total['results']), expected_total_len)
        self.assertEqual(total['total'], expected_total_len)

        returned_total = round(
            sum(r.get('rate', r.get('price')) for r in total['results']), 5)
        self.assertLessEqual(
            abs(expected_total - float(returned_total)), 0.0001)

        returned_qty = round(sum(r['qty'] for r in total['results']), 5)
        self.assertLessEqual(
            abs(expected_qty - float(returned_qty)), 0.0001)

    def test_get_total_all_scopes_all_periods(self):
        expected_total, expected_qty, _ = self._expected_total_qty_len(
            self.data)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 4)

        self._compare_get_total_result_with_expected(
            expected_qty,
            expected_total,
            1,
            self.storage.total(begin=begin, end=end))

    def test_get_total_one_scope_all_periods(self):
        expected_total, expected_qty, _ = self._expected_total_qty_len(
            self.data, self._project_id)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 4)

        filters = {'project_id': self._project_id}
        self._compare_get_total_result_with_expected(
            expected_qty,
            expected_total,
            1,
            self.storage.total(begin=begin,
                               end=end,
                               filters=filters),
        )

    def test_get_total_all_scopes_one_period(self):
        expected_total, expected_qty, _ = self._expected_total_qty_len(
            [self.data[0]])

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 1)

        self._compare_get_total_result_with_expected(
            expected_qty,
            expected_total,
            1,
            self.storage.total(begin=begin, end=end))

    def test_get_total_one_scope_one_period(self):
        expected_total, expected_qty, _ = self._expected_total_qty_len(
            [self.data[0]], self._project_id)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 1)

        filters = {'project_id': self._project_id}
        self._compare_get_total_result_with_expected(
            expected_qty,
            expected_total,
            1,
            self.storage.total(begin=begin,
                               end=end,
                               filters=filters),
        )

    def test_get_total_all_scopes_all_periods_groupby_project_id(self):
        expected_total_first, expected_qty_first, _ = \
            self._expected_total_qty_len(self.data, self._project_id)
        expected_total_second, expected_qty_second, _ = \
            self._expected_total_qty_len(self.data, self._other_project_id)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 4)
        total = self.storage.total(begin=begin, end=end,
                                   groupby=['project_id'])
        self.assertEqual(len(total['results']), 2)
        self.assertEqual(total['total'], 2)

        for t in total['results']:
            self.assertIn('project_id', t.keys())

        total['results'].sort(key=lambda x: x['project_id'], reverse=True)

        first_element = total['results'][0]
        self.assertLessEqual(
            abs(round(
                float(first_element.get('rate', first_element.get('price')))
                - expected_total_first, 5)),
            0.0001,
        )
        second_element = total['results'][1]
        self.assertLessEqual(
            abs(round(
                float(second_element.get('rate', second_element.get('price')))
                - expected_total_second, 5)),
            0.0001,
        )
        self.assertLessEqual(
            abs(round(float(total['results'][0]['qty'])
                      - expected_qty_first, 5)),
            0.0001,
        )
        self.assertLessEqual(
            abs(round(float(total['results'][1]['qty'])
                      - expected_qty_second, 5)),
            0.0001,
        )

    def test_get_total_all_scopes_one_period_groupby_project_id(self):
        expected_total_first, expected_qty_first, _ = \
            self._expected_total_qty_len([self.data[0]], self._project_id)
        expected_total_second, expected_qty_second, _ = \
            self._expected_total_qty_len([self.data[0]],
                                         self._other_project_id)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 1)
        total = self.storage.total(begin=begin, end=end,
                                   groupby=['project_id'])
        self.assertEqual(len(total), 2)

        for t in total['results']:
            self.assertIn('project_id', t.keys())

        total['results'].sort(key=lambda x: x['project_id'], reverse=True)

        first_entry = total['results'][0]
        second_entry = total['results'][1]
        self.assertLessEqual(
            abs(round(float(first_entry.get('rate', first_entry.get('price')))
                      - expected_total_first, 5)),
            0.0001,
        )
        self.assertLessEqual(
            abs(round(
                float(second_entry.get('rate', second_entry.get('price')))
                - expected_total_second, 5)),
            0.0001,
        )
        self.assertLessEqual(
            abs(round(float(total['results'][0]['qty'])
                      - expected_qty_first, 5)),
            0.0001,
        )
        self.assertLessEqual(
            abs(round(float(total['results'][1]['qty'])
                      - expected_qty_second, 5)),
            0.0001,
        )

    def test_get_total_all_scopes_all_periods_groupby_type_paginate(self):
        expected_total, expected_qty, _ = \
            self._expected_total_qty_len(self.data)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 4)

        total = {'total': 0, 'results': []}
        for offset in range(0, 7, 2):
            chunk = self.storage.total(
                begin=begin,
                end=end,
                offset=offset,
                limit=2,
                groupby=['type'])
            # there are seven metric types
            self.assertEqual(chunk['total'], 7)
            # last chunk, shorter
            if offset == 6:
                self.assertEqual(len(chunk['results']), 1)
            else:
                self.assertEqual(len(chunk['results']), 2)
            total['results'] += chunk['results']
            total['total'] += len(chunk['results'])

        unpaginated_total = self.storage.total(
            begin=begin, end=end, groupby=['type'])
        self.assertEqual(total, unpaginated_total)

        self._compare_get_total_result_with_expected(
            expected_qty,
            expected_total,
            7,
            total)

    def test_retrieve_all_scopes_all_types(self):
        expected_total, expected_qty, expected_length = \
            self._expected_total_qty_len(self.data)

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 4)

        frames = self.storage.retrieve(begin=begin, end=end)
        self.assertEqual(frames['total'], expected_length)

        retrieved_length = sum(len(list(frame.iterpoints()))
                               for frame in frames['dataframes'])

        self.assertEqual(expected_length, retrieved_length)

    def test_retrieve_all_scopes_one_type(self):
        expected_total, expected_qty, expected_length = \
            self._expected_total_qty_len(self.data, types=['image.size'])

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 4)

        frames = self.storage.retrieve(begin=begin, end=end,
                                       metric_types=['image.size'])
        self.assertEqual(frames['total'], expected_length)

        retrieved_length = sum(len(list(frame.iterpoints()))
                               for frame in frames['dataframes'])

        self.assertEqual(expected_length, retrieved_length)

    def test_retrieve_one_scope_two_types_one_period(self):
        expected_total, expected_qty, expected_length = \
            self._expected_total_qty_len([self.data[0]], self._project_id,
                                         types=['image.size', 'instance'])

        begin = datetime.datetime(2018, 1, 1)
        end = datetime.datetime(2018, 1, 1, 1)

        filters = {'project_id': self._project_id}
        frames = self.storage.retrieve(begin=begin, end=end,
                                       filters=filters,
                                       metric_types=['image.size', 'instance'])
        self.assertEqual(frames['total'], expected_length)

        retrieved_length = sum(len(list(frame.iterpoints()))
                               for frame in frames['dataframes'])

        self.assertEqual(expected_length, retrieved_length)

    def test_parse_groupby_syntax_to_groupby_elements_no_time_groupby(self):
        groupby = ["something"]

        out = self.storage.parse_groupby_syntax_to_groupby_elements(groupby)

        self.assertEqual(groupby, out)

    def test_parse_groupby_syntax_to_groupby_elements_time_groupby(self):
        groupby = ["something", "time"]

        out = self.storage.parse_groupby_syntax_to_groupby_elements(groupby)

        self.assertEqual(groupby, out)

    def test_parse_groupby_syntax_to_groupby_elements_odd_time(self):
        groupby = ["something", "time-odd-time-element"]

        with mock.patch.object(storage.v2.LOG, 'warning') as log_mock:
            out = self.storage.parse_groupby_syntax_to_groupby_elements(
                groupby)
            log_mock.assert_has_calls([
                mock.call("The groupby [%s] command is not expected for "
                          "storage backend [%s]. Therefore, we leave it as "
                          "is.", "time-odd-time-element", self.storage)])

        self.assertEqual(groupby, out)

    def test_parse_groupby_syntax_to_groupby_elements_wrong_time_frame(self):
        groupby = ["something", "time-u"]

        expected_message = r"400 Bad Request: Invalid groupby time option. " \
                           r"There is no groupby processing for \[time-u\]."

        self.assertRaisesRegex(
            http_exceptions.BadRequest, expected_message,
            self.storage.parse_groupby_syntax_to_groupby_elements,
            groupby)

    def test_parse_groupby_syntax_to_groupby_elements_all_time_options(self):
        groupby = ["something", "time", "time-d", "time-w", "time-m", "time-y"]

        expected_log_calls = []
        for k, v in storage.v2.BaseStorage.TIME_COMMANDS_MAP.items():
            expected_log_calls.append(
                mock.call("Replacing API groupby time command [%s] with "
                          "internal groupby command [%s].", "time-%s" % k, v))

        with mock.patch.object(storage.v2.LOG, 'debug') as log_debug_mock:
            out = self.storage.parse_groupby_syntax_to_groupby_elements(
                groupby)
            log_debug_mock.assert_has_calls(expected_log_calls)

        self.assertEqual(["something", "time", "day_of_the_year",
                          "week_of_the_year", "month", "year"], out)

    def test_parse_groupby_syntax_to_groupby_elements_no_groupby(self):
        with mock.patch.object(storage.v2.LOG, 'debug') as log_debug_mock:
            out = self.storage.parse_groupby_syntax_to_groupby_elements(None)
            log_debug_mock.assert_has_calls([
                mock.call("No groupby to process syntax.")])

            self.assertIsNone(out)


StorageUnitTest.generate_scenarios()
