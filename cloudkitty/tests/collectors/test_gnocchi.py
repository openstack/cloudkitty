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
import datetime
from unittest import mock

from dateutil import tz

from cloudkitty.collector import gnocchi
from cloudkitty import tests
from cloudkitty.tests import samples


class GnocchiCollectorTest(tests.TestCase):
    def setUp(self):
        super(GnocchiCollectorTest, self).setUp()
        self._tenant_id = samples.TENANT
        self.conf.set_override('collector', 'gnocchi', 'collect')
        self.conf.set_override(
            'gnocchi_auth_type', 'basic', 'collector_gnocchi')

        self.collector = gnocchi.GnocchiCollector(
            period=3600,
            conf=samples.DEFAULT_METRICS_CONF,
        )

    def test_format_data_raises_exception(self):
        metconf = {'extra_args': {'resource_key': 'id'}}
        data = {'group': {'id': '281b9dc6-5d02-4610-af2d-10d0d6887f48'}}
        self.assertRaises(
            gnocchi.AssociatedResourceNotFound,
            self.collector._format_data,
            metconf,
            data,
            resources_info={},
        )

    # Filter generation
    def test_generate_one_field_filter(self):
        actual = self.collector.gen_filter(value1=2)
        expected = {
            '=': {
                'value1': 2
            }}
        self.assertEqual(expected, actual)

    def test_generate_two_fields_filter(self):
        actual = self.collector.gen_filter(value1=2, value2=3)
        expected = {'and': [{
            '=': {
                'value1': 2
            }}, {
            '=': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_collector_retrieve_metrics(self):
        expected_data = {"group": {"id": "id-1",
                                   "revision_start": datetime.datetime(
                                       2020, 1, 1, 1, 10, 0, tzinfo=tz.tzutc())
                                   }}

        data = [
            {"group": {"id": "id-1", "revision_start": datetime.datetime(
                2020, 1, 1, tzinfo=tz.tzutc())}},
            expected_data
        ]

        no_response = mock.patch(

            'cloudkitty.collector.gnocchi.GnocchiCollector.fetch_all',
            return_value=data,
        )

        for c in self.collector.conf:
            with no_response:
                actual_name, actual_data = self.collector.retrieve(
                    metric_name=c,
                    start=samples.FIRST_PERIOD_BEGIN,
                    end=samples.FIRST_PERIOD_END,
                    project_id=samples.TENANT,
                    q_filter=None,
                )

    def test_generate_two_fields_filter_different_operations(self):
        actual = self.collector.gen_filter(
            cop='>=',
            lop='or',
            value1=2,
            value2=3)
        expected = {'or': [{
            '>=': {
                'value1': 2
            }}, {
            '>=': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_generate_two_filters_and_add_logical(self):
        filter1 = self.collector.gen_filter(value1=2)
        filter2 = self.collector.gen_filter(cop='>', value2=3)
        actual = self.collector.extend_filter(filter1, filter2, lop='or')
        expected = {'or': [{
            '=': {
                'value1': 2
            }}, {
            '>': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_noop_on_single_filter(self):
        filter1 = self.collector.gen_filter(value1=2)
        actual = self.collector.extend_filter(filter1, lop='or')
        self.assertEqual(filter1, actual)

    def test_try_extend_empty_filter(self):
        actual = self.collector.extend_filter()
        self.assertEqual({}, actual)
        actual = self.collector.extend_filter(actual, actual)
        self.assertEqual({}, actual)

    def test_try_extend_filter_with_none(self):
        filter1 = self.collector.gen_filter(value1=2)
        actual = self.collector.extend_filter(filter1, None)
        self.assertEqual(filter1, actual)

    def test_generate_two_logical_ops(self):
        filter1 = self.collector.gen_filter(value1=2, value2=3)
        filter2 = self.collector.gen_filter(cop='<=', value3=1)
        actual = self.collector.extend_filter(filter1, filter2, lop='or')
        expected = {'or': [{
            'and': [{
                '=': {
                    'value1': 2
                }}, {
                '=': {
                    'value2': 3
                }}]}, {
            '<=': {
                'value3': 1
            }}]}
        self.assertEqual(expected, actual)

    def test_gen_filter_parameters(self):
        actual = self.collector.gen_filter(
            cop='>',
            lop='or',
            value1=2,
            value2=3)
        expected = {'or': [{
            '>': {
                'value1': 2
            }}, {
            '>': {
                'value2': 3
            }}]}
        self.assertEqual(expected, actual)

    def test_extend_filter_parameters(self):
        actual = self.collector.extend_filter(
            ['dummy1'],
            ['dummy2'],
            lop='or')
        expected = {'or': ['dummy1', 'dummy2']}
        self.assertEqual(expected, actual)


class GnocchiCollectorAggregationOperationTest(tests.TestCase):

    def setUp(self):
        super(GnocchiCollectorAggregationOperationTest, self).setUp()
        self.conf.set_override('collector', 'gnocchi', 'collect')
        self.start = datetime.datetime(2019, 1, 1, tzinfo=tz.tzutc())
        self.end = datetime.datetime(2019, 1, 1, 1, tzinfo=tz.tzutc())

    def do_test(self, expected_op, extra_args=None, conf=None):
        conf = conf or {
            'metrics': {
                'metric_one': {
                    'unit': 'GiB',
                    'groupby': ['project_id'],
                    'extra_args': extra_args if extra_args else {},
                }
            }
        }

        coll = gnocchi.GnocchiCollector(period=3600, conf=conf)

        for c in coll.conf:
            with mock.patch.object(coll._conn.aggregates,
                                   'fetch') as fetch_mock:
                coll._fetch_metric(c, self.start, self.end)
                fetch_mock.assert_called_once_with(
                    expected_op,
                    groupby=['project_id', 'id'],
                    resource_type='resource_x',
                    search={'=': {'type': 'resource_x'}},
                    start=self.start, stop=self.end,
                    granularity=3600,
                    use_history=True
                )

    def test_multiple_confs(self):
        conf = {
            'metrics': {
                'metric_one': [{
                    'alt_name': 'foo',
                    'unit': 'GiB',
                    'groupby': ['project_id'],
                    'extra_args': {'resource_type': 'resource_x'},
                }, {
                    'alt_name': 'bar',
                    'unit': 'GiB',
                    'groupby': ['project_id'],
                    'extra_args': {'resource_type': 'resource_x'},
                }]
            }
        }
        expected_op = ["aggregate", "max", ["metric", "metric_one", "max"]]
        self.do_test(expected_op, conf=conf)

    def test_no_agg_no_re_agg(self):
        extra_args = {'resource_type': 'resource_x'}
        expected_op = ["aggregate", "max", ["metric", "metric_one", "max"]]
        self.do_test(expected_op, extra_args=extra_args)

    def test_custom_agg_no_re_agg(self):
        extra_args = {
            'resource_type': 'resource_x',
            'aggregation_method': 'mean',
        }
        expected_op = ["aggregate", "max", ["metric", "metric_one", "mean"]]
        self.do_test(expected_op, extra_args=extra_args)

    def test_no_agg_custom_re_agg(self):
        extra_args = {
            'resource_type': 'resource_x',
            're_aggregation_method': 'sum',
        }
        expected_op = ["aggregate", "sum", ["metric", "metric_one", "max"]]
        self.do_test(expected_op, extra_args=extra_args)

    def test_custom_agg_custom_re_agg(self):
        extra_args = {
            'resource_type': 'resource_x',
            'aggregation_method': 'rate:mean',
            're_aggregation_method': 'sum',
        }
        expected_op = [
            "aggregate", "sum",
            ["metric", "metric_one", "rate:mean"],
        ]
        self.do_test(expected_op, extra_args=extra_args)

    def test_filter_unecessary_measurements_use_all_datapoints(self):
        data = [
            {"group":
                {
                    "id": "id-1",
                    "revision_start": datetime.datetime(
                        2020, 1, 1, tzinfo=tz.tzutc())}},
            {"group":
                {"id": "id-1",
                 "revision_start": datetime.datetime(
                     2020, 1, 1, 1, 10, 0, tzinfo=tz.tzutc())}}
        ]

        expected_data = data.copy()
        metric_name = 'test_metric'
        metric = {
            'name': metric_name,
            'extra_args': {'use_all_resource_revisions': True}}

        data_filtered = gnocchi.GnocchiCollector.\
            filter_unecessary_measurements(data, metric, metric_name)

        self.assertEqual(expected_data, data_filtered)

    def test_filter_unecessary_measurements_use_only_last_datapoint(self):
        expected_data = {"group": {"id": "id-1",
                                   "revision_start": datetime.datetime(
                                       2020, 1, 1, 1, 10, 0, tzinfo=tz.tzutc())
                                   }}

        data = [
            {"group": {"id": "id-1", "revision_start": datetime.datetime(
                     2020, 1, 1, tzinfo=tz.tzutc())}},
            expected_data
        ]

        metric_name = 'test_metric'
        metric = {'name': metric_name, 'extra_args': {
            'use_all_resource_revisions': False}}

        data_filtered = gnocchi.GnocchiCollector.\
            filter_unecessary_measurements(data, metric, metric_name)

        data_filtered = list(data_filtered)
        self.assertEqual(1, len(data_filtered))
        self.assertEqual(expected_data, data_filtered[0])

    def test_generate_aggregation_operation_same_reaggregation(self):
        metric_name = "test"
        extra_args = {"aggregation_method": 'mean'}

        expected_op = ["aggregate", 'mean', ["metric", "test", 'mean']]

        op = gnocchi.GnocchiCollector.generate_aggregation_operation(
            extra_args, metric_name)

        self.assertEqual(expected_op, op)

    def test_generate_aggregation_operation_different_reaggregation(self):
        metric_name = "test"
        extra_args = {"aggregation_method": 'mean',
                      "re_aggregation_method": 'max'}

        expected_op = ["aggregate", 'max', ["metric", "test", 'mean']]

        op = gnocchi.GnocchiCollector.generate_aggregation_operation(
            extra_args, metric_name)

        self.assertEqual(expected_op, op)

    def test_generate_aggregation_operation_custom_query(self):
        metric_name = "test"
        extra_args = {"aggregation_method": 'mean',
                      "re_aggregation_method": 'max',
                      "custom_query":
                          "(* (aggregate RE_AGGREGATION_METHOD (metric "
                          "METRIC_NAME AGGREGATION_METHOD)) -1)"}

        expected_op = "(* (aggregate max (metric test mean)) -1)"

        op = gnocchi.GnocchiCollector.generate_aggregation_operation(
            extra_args, metric_name)

        self.assertEqual(expected_op, op)
