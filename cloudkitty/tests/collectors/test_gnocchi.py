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

    def do_test(self, expected_op, extra_args=None):
        conf = {
            'metrics': {
                'metric_one': {
                    'unit': 'GiB',
                    'groupby': ['project_id'],
                    'extra_args': extra_args if extra_args else {},
                }
            }
        }

        coll = gnocchi.GnocchiCollector(period=3600, conf=conf)
        with mock.patch.object(coll._conn.aggregates, 'fetch') as fetch_mock:
            coll._fetch_metric('metric_one', self.start, self.end)
            fetch_mock.assert_called_once_with(
                expected_op,
                groupby=['project_id', 'id'],
                resource_type='resource_x',
                search={'=': {'type': 'resource_x'}},
                start=self.start, stop=self.end,
                granularity=3600
            )

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
