# -*- coding: utf-8 -*-
# Copyright 2019 Objectif Libre
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
from unittest import mock

from cloudkitty.collector import prometheus
from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty.utils import json


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
