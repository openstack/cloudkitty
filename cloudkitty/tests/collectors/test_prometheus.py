# -*- coding: utf-8 -*-
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
from decimal import Decimal
from unittest import mock

from cloudkitty import collector
from cloudkitty.collector import exceptions
from cloudkitty.collector import prometheus
from cloudkitty.common.prometheus_client import PrometheusResponseError
from cloudkitty import dataframe
from cloudkitty import tests
from cloudkitty.tests import samples


class PrometheusCollectorTest(tests.TestCase):
    def setUp(self):
        super(PrometheusCollectorTest, self).setUp()
        self._tenant_id = samples.TENANT
        args = {
            'period': 3600,
            'scope_key': 'namespace',
            'conf': {
                'metrics': {
                    'http_requests_total': {
                        'unit': 'instance',
                        'groupby': [
                            'foo',
                            'bar',
                        ],
                        'metadata': [
                            'code',
                            'instance',
                        ],
                        'extra_args': {
                            'aggregation_method': 'avg'
                        },
                    },
                }
            }
        }
        args_range_function = {
            'period': 3600,
            'scope_key': 'namespace',
            'conf': {
                'metrics': {
                    'http_requests_total': {
                        'unit': 'instance',
                        'groupby': [
                            'foo',
                            'bar',
                        ],
                        'metadata': [
                            'code',
                            'instance',
                        ],
                        'extra_args': {
                            'aggregation_method': 'avg',
                            'query_function': 'abs',
                        },
                    },
                }
            }
        }
        args_query_function = {
            'period': 3600,
            'scope_key': 'namespace',
            'conf': {
                'metrics': {
                    'http_requests_total': {
                        'unit': 'instance',
                        'groupby': [
                            'foo',
                            'bar',
                        ],
                        'metadata': [
                            'code',
                            'instance',
                        ],
                        'extra_args': {
                            'aggregation_method': 'avg',
                            'range_function': 'delta',
                        },
                    },
                }
            }
        }
        args_all = {
            'period': 3600,
            'scope_key': 'namespace',
            'conf': {
                'metrics': {
                    'http_requests_total': {
                        'unit': 'instance',
                        'groupby': [
                            'foo',
                            'bar',
                        ],
                        'metadata': [
                            'code',
                            'instance',
                        ],
                        'extra_args': {
                            'aggregation_method': 'avg',
                            'range_function': 'delta',
                            'query_function': 'abs',
                        },
                    },
                }
            }
        }
        self.collector_mandatory = prometheus.PrometheusCollector(**args)
        self.collector_without_range_function = prometheus.PrometheusCollector(
            **args_range_function)
        self.collector_without_query_function = prometheus.PrometheusCollector(
            **args_query_function)
        self.collector_all = prometheus.PrometheusCollector(**args_all)

    def test_fetch_all_build_query_only_mandatory(self):
        query = (
            'avg(avg_over_time(http_requests_total'
            '{project_id="f266f30b11f246b589fd266f85eeec39"}[3600s]'
            ')) by (foo, bar, project_id, code, instance)'
        )

        with mock.patch.object(
            prometheus.PrometheusClient, 'get_instant',
        ) as mock_get:
            self.collector_mandatory.fetch_all(
                'http_requests_total',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                self._tenant_id,
            )
            mock_get.assert_called_once_with(
                query,
                samples.FIRST_PERIOD_END.isoformat(),
            )

    def test_fetch_all_build_query_without_range_function(self):
        query = (
            'avg(abs(avg_over_time(http_requests_total'
            '{project_id="f266f30b11f246b589fd266f85eeec39"}[3600s]'
            '))) by (foo, bar, project_id, code, instance)'
        )

        with mock.patch.object(
            prometheus.PrometheusClient, 'get_instant',
        ) as mock_get:
            self.collector_without_range_function.fetch_all(
                'http_requests_total',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                self._tenant_id,
            )
            mock_get.assert_called_once_with(
                query,
                samples.FIRST_PERIOD_END.isoformat(),
            )

    def test_fetch_all_build_query_without_query_function(self):
        query = (
            'avg(delta(http_requests_total'
            '{project_id="f266f30b11f246b589fd266f85eeec39"}[3600s]'
            ')) by (foo, bar, project_id, code, instance)'
        )

        with mock.patch.object(
            prometheus.PrometheusClient, 'get_instant',
        ) as mock_get:
            self.collector_without_query_function.fetch_all(
                'http_requests_total',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                self._tenant_id,
            )
            mock_get.assert_called_once_with(
                query,
                samples.FIRST_PERIOD_END.isoformat(),
            )

    def test_fetch_all_build_query_all(self):
        query = (
            'avg(abs(delta(http_requests_total'
            '{project_id="f266f30b11f246b589fd266f85eeec39"}[3600s]'
            '))) by (foo, bar, project_id, code, instance)'
        )

        with mock.patch.object(
            prometheus.PrometheusClient, 'get_instant',
        ) as mock_get:
            self.collector_all.fetch_all(
                'http_requests_total',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                self._tenant_id,
            )
            mock_get.assert_called_once_with(
                query,
                samples.FIRST_PERIOD_END.isoformat(),
            )

    def test_format_data_instant_query(self):
        expected = ({
            'code': '200',
            'instance': 'localhost:9090',
        }, {
            'bar': '',
            'foo': '',
            'project_id': ''
        }, Decimal('7'))

        params = {
            'metric_name': 'http_requests_total',
            'scope_key': 'project_id',
            'scope_id': self._tenant_id,
            'start': samples.FIRST_PERIOD_BEGIN,
            'end': samples.FIRST_PERIOD_END,
            'data': samples.PROMETHEUS_RESP_INSTANT_QUERY['data']['result'][0],
        }
        actual = self.collector_mandatory._format_data(**params)
        self.assertEqual(expected, actual)

    def test_format_data_instant_query_2(self):
        expected = ({
            'code': '200',
            'instance': 'localhost:9090',
        }, {
            'bar': '',
            'foo': '',
            'project_id': ''
        }, Decimal('42'))

        params = {
            'metric_name': 'http_requests_total',
            'scope_key': 'project_id',
            'scope_id': self._tenant_id,
            'start': samples.FIRST_PERIOD_BEGIN,
            'end': samples.FIRST_PERIOD_END,
            'data': samples.PROMETHEUS_RESP_INSTANT_QUERY['data']['result'][1],
        }
        actual = self.collector_mandatory._format_data(**params)
        self.assertEqual(expected, actual)

    def test_format_retrieve(self):
        expected_name = 'http_requests_total'
        group_by = {'bar': '', 'foo': '', 'project_id': '',
                    'week_of_the_year': '00', 'day_of_the_year': '1',
                    'month': '1', 'year': '2015'}

        expected_data = [
            dataframe.DataPoint(
                'instance', '7', '0', group_by,
                {'code': '200', 'instance': 'localhost:9090'}),
            dataframe.DataPoint(
                'instance', '42', '0', group_by,
                {'code': '200', 'instance': 'localhost:9090'}),
        ]

        no_response = mock.patch(
            'cloudkitty.common.prometheus_client.PrometheusClient.get_instant',
            return_value=samples.PROMETHEUS_RESP_INSTANT_QUERY,
        )

        with no_response:
            actual_name, actual_data = self.collector_mandatory.retrieve(
                metric_name='http_requests_total',
                start=samples.FIRST_PERIOD_BEGIN,
                end=samples.FIRST_PERIOD_END,
                project_id=samples.TENANT,
                q_filter=None,
            )

        self.assertEqual(expected_name, actual_name)
        self.assertEqual(expected_data, actual_data)

    def test_format_retrieve_raise_NoDataCollected(self):
        no_response = mock.patch(
            'cloudkitty.common.prometheus_client.PrometheusClient.get_instant',
            return_value=samples.PROMETHEUS_EMPTY_RESP_INSTANT_QUERY,
        )

        with no_response:
            self.assertRaises(
                collector.NoDataCollected,
                self.collector_mandatory.retrieve,
                metric_name='http_requests_total',
                start=samples.FIRST_PERIOD_BEGIN,
                end=samples.FIRST_PERIOD_END,
                project_id=samples.TENANT,
                q_filter=None,
            )

    def test_format_retrieve_all_raises_exception(self):
        invalid_response = mock.patch(
            'cloudkitty.common.prometheus_client.PrometheusClient.get_instant',
            side_effect=PrometheusResponseError,
        )

        with invalid_response:
            self.assertRaises(
                exceptions.CollectError,
                self.collector_mandatory.retrieve,
                metric_name='http_requests_total',
                start=samples.FIRST_PERIOD_BEGIN,
                end=samples.FIRST_PERIOD_END,
                project_id=samples.TENANT,
                q_filter=None,
            )
