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
import testtools

from cloudkitty import collector
from cloudkitty.collector import prometheus
from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty.tests.utils import is_functional_test
from cloudkitty import transformer


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class PrometheusCollectorTest(tests.TestCase):
    def setUp(self):
        super(PrometheusCollectorTest, self).setUp()
        self._tenant_id = samples.TENANT
        args = {
            'period': 3600,
            'conf': {
                'metrics': {
                    'http_requests_total': {
                        'unit': 'instance',
                        'extra_args': {
                            'query': 'http_request_total[$period]',
                        },
                    },
                }
            }
        }
        transformers = transformer.get_transformers()
        self.collector = prometheus.PrometheusCollector(transformers, **args)

    def test_format_data_instant_query(self):
        expected = ({}, {}, Decimal('7'))

        params = {
            'metric_name': 'http_requests_total',
            'project_id': self._tenant_id,
            'start': samples.FIRST_PERIOD_BEGIN,
            'end': samples.FIRST_PERIOD_END,
            'data': samples.PROMETHEUS_RESP_INSTANT_QUERY['data']['result'][0],
        }
        actual = self.collector._format_data(**params)
        self.assertEqual(expected, actual)

    def test_format_data_instant_query_2(self):
        expected = ({}, {}, Decimal('42'))

        params = {
            'metric_name': 'http_requests_total',
            'project_id': self._tenant_id,
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
                    'desc': {},
                    'groupby': {},
                    'metadata': {},
                    'vol': {
                        'qty': Decimal('7'),
                        'unit': 'instance'
                    }
                },
                {
                    'desc': {},
                    'groupby': {},
                    'metadata': {},
                    'vol': {
                        'qty': Decimal('42'),
                        'unit': 'instance'
                    }
                }

            ]
        }

        no_response = mock.patch(
            'cloudkitty.collector.prometheus.PrometheusClient.get_data',
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
            'cloudkitty.collector.prometheus.PrometheusClient.get_data',
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


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class PrometheusClientTest(tests.TestCase):
    def setUp(self):
        super(PrometheusClientTest, self).setUp()
        self.client = prometheus.PrometheusClient

    def test_build_instant_query_first_period(self):
        expected = 'http://localhost:9090/api/v1/query?' \
                   'query=increase(http_requests_total[3600s])' \
                   '&time=2015-01-01T01:00:00Z'
        params = {
            'source': 'http://localhost:9090/api/v1',
            'query': 'increase(http_requests_total[$period])',
            'start': samples.FIRST_PERIOD_BEGIN,
            'end': samples.FIRST_PERIOD_END,
            'period': '3600',
            'metric_name': 'http_requests_total',
        }
        actual = self.client.build_query(**params)
        self.assertEqual(expected, actual)

    def test_build_instant_query_second_period(self):
        expected = 'http://localhost:9090/api/v1/query?' \
                   'query=increase(http_requests_total[3600s])' \
                   '&time=2015-01-01T02:00:00Z'
        params = {
            'source': 'http://localhost:9090/api/v1',
            'query': 'increase(http_requests_total[$period])',
            'start': samples.SECOND_PERIOD_BEGIN,
            'end': samples.SECOND_PERIOD_END,
            'period': '3600',
            'metric_name': 'http_requests_total',
        }
        actual = self.client.build_query(**params)
        self.assertEqual(expected, actual)
