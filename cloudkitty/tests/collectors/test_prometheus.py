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
# @author: Martin CAMEY
#
from decimal import Decimal

import mock

from cloudkitty import collector
from cloudkitty.collector import prometheus
from cloudkitty import json_utils as json
from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty import transformer


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
                            'aggregation_method': 'avg',
                        },
                    },
                }
            }
        }
        transformers = transformer.get_transformers()
        self.collector = prometheus.PrometheusCollector(transformers, **args)

    def test_fetch_all_build_query(self):
        query = (
            'avg(avg_over_time(http_requests_total'
            '{project_id="f266f30b11f246b589fd266f85eeec39"}[3600s]'
            ')) by (foo, bar, project_id, code, instance)'
        )

        with mock.patch.object(
            prometheus.PrometheusClient, 'get_instant',
        ) as mock_get:
            self.collector.fetch_all(
                'http_requests_total',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                self._tenant_id,
            )
            mock_get.assert_called_once_with(
                query,
                samples.FIRST_PERIOD_END,
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
        actual = self.collector._format_data(**params)
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
        actual = self.collector._format_data(**params)
        self.assertEqual(expected, actual)

    def test_format_retrieve(self):
        expected = {
            'http_requests_total': [
                {
                    'desc': {
                        'bar': '', 'foo': '', 'project_id': '',
                        'code': '200', 'instance': 'localhost:9090',
                    },
                    'groupby': {'bar': '', 'foo': '', 'project_id': ''},
                    'metadata': {'code': '200', 'instance': 'localhost:9090'},
                    'vol': {
                        'qty': Decimal('7'),
                        'unit': 'instance'
                    }
                },
                {
                    'desc': {
                        'bar': '', 'foo': '', 'project_id': '',
                        'code': '200', 'instance': 'localhost:9090',
                    },
                    'groupby': {'bar': '', 'foo': '', 'project_id': ''},
                    'metadata': {'code': '200', 'instance': 'localhost:9090'},
                    'vol': {
                        'qty': Decimal('42'),
                        'unit': 'instance'
                    }
                }
            ]
        }

        no_response = mock.patch(
            'cloudkitty.collector.prometheus.PrometheusClient.get_instant',
            return_value=samples.PROMETHEUS_RESP_INSTANT_QUERY,
        )

        with no_response:
            actual = self.collector.retrieve(
                metric_name='http_requests_total',
                start=samples.FIRST_PERIOD_BEGIN,
                end=samples.FIRST_PERIOD_END,
                project_id=samples.TENANT,
                q_filter=None,
            )

        self.assertEqual(expected, actual)

    def test_format_retrieve_raise_NoDataCollected(self):
        no_response = mock.patch(
            'cloudkitty.collector.prometheus.PrometheusClient.get_instant',
            return_value=samples.PROMETHEUS_EMPTY_RESP_INSTANT_QUERY,
        )

        with no_response:
            self.assertRaises(
                collector.NoDataCollected,
                self.collector.retrieve,
                metric_name='http_requests_total',
                start=samples.FIRST_PERIOD_BEGIN,
                end=samples.FIRST_PERIOD_END,
                project_id=samples.TENANT,
                q_filter=None,
            )


class PrometheusClientTest(tests.TestCase):
    class FakeResponse(object):
        """Mimics an HTTP ``requests`` response"""

        def __init__(self, url, text, status_code):
            self.url = url
            self.text = text
            self.status_code = status_code

        def json(self):
            return json.loads(self.text)

    @staticmethod
    def _mock_requests_get(text):
        """Factory to build FakeResponse with desired response body text"""
        return lambda *args, **kwargs: PrometheusClientTest.FakeResponse(
            args[0], text, 200,
        )

    def setUp(self):
        super(PrometheusClientTest, self).setUp()
        self.client = prometheus.PrometheusClient(
            'http://localhost:9090/api/v1',
        )

    def test_get_with_no_options(self):
        with mock.patch('requests.get') as mock_get:
            self.client._get(
                'query_range',
                params={
                    'query': 'max(http_requests_total) by (project_id)',
                    'start': samples.FIRST_PERIOD_BEGIN,
                    'end': samples.FIRST_PERIOD_END,
                    'step': 10,
                },
            )
            mock_get.assert_called_once_with(
                'http://localhost:9090/api/v1/query_range',
                params={
                    'query': 'max(http_requests_total) by (project_id)',
                    'start': samples.FIRST_PERIOD_BEGIN,
                    'end': samples.FIRST_PERIOD_END,
                    'step': 10,
                },
                auth=None,
                verify=True,
            )

    def test_get_with_options(self):
        client = prometheus.PrometheusClient(
            'http://localhost:9090/api/v1',
            auth=('foo', 'bar'),
            verify='/some/random/path',
        )
        with mock.patch('requests.get') as mock_get:
            client._get(
                'query_range',
                params={
                    'query': 'max(http_requests_total) by (project_id)',
                    'start': samples.FIRST_PERIOD_BEGIN,
                    'end': samples.FIRST_PERIOD_END,
                    'step': 10,
                },
            )
            mock_get.assert_called_once_with(
                'http://localhost:9090/api/v1/query_range',
                params={
                    'query': 'max(http_requests_total) by (project_id)',
                    'start': samples.FIRST_PERIOD_BEGIN,
                    'end': samples.FIRST_PERIOD_END,
                    'step': 10,
                },
                auth=('foo', 'bar'),
                verify='/some/random/path',
            )

    def test_get_instant(self):
        mock_get = mock.patch(
            'requests.get',
            side_effect=self._mock_requests_get('{"foo": "bar"}'),
        )

        with mock_get:
            res = self.client.get_instant(
                'max(http_requests_total) by (project_id)',
            )
            self.assertEqual(res, {'foo': 'bar'})

    def test_get_range(self):
        mock_get = mock.patch(
            'requests.get',
            side_effect=self._mock_requests_get('{"foo": "bar"}'),
        )

        with mock_get:
            res = self.client.get_range(
                'max(http_requests_total) by (project_id)',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                10,
            )
            self.assertEqual(res, {'foo': 'bar'})

    def test_get_instant_raises_error_on_bad_json(self):
        # Simulating malformed JSON response from HTTP+PromQL instant request
        mock_get = mock.patch(
            'requests.get',
            side_effect=self._mock_requests_get('{"foo": "bar"'),
        )
        with mock_get:
            self.assertRaises(
                prometheus.PrometheusResponseError,
                self.client.get_instant,
                'max(http_requests_total) by (project_id)',
            )

    def test_get_range_raises_error_on_bad_json(self):
        # Simulating malformed JSON response from HTTP+PromQL range request
        mock_get = mock.patch(
            'requests.get',
            side_effect=self._mock_requests_get('{"foo": "bar"'),
        )
        with mock_get:
            self.assertRaises(
                prometheus.PrometheusResponseError,
                self.client.get_range,
                'max(http_requests_total) by (project_id)',
                samples.FIRST_PERIOD_BEGIN,
                samples.FIRST_PERIOD_END,
                10,
            )
