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
#
from unittest import mock

from cloudkitty.common.prometheus_client import PrometheusClient
from cloudkitty.common.prometheus_client import PrometheusResponseError
from cloudkitty.fetcher import prometheus
from cloudkitty import tests


class PrometheusFetcherTest(tests.TestCase):
    def setUp(self):
        super(PrometheusFetcherTest, self).setUp()
        self.conf.set_override(
            'metric', 'http_requests_total', 'fetcher_prometheus',
        )
        self.conf.set_override(
            'scope_attribute', 'namespace', 'fetcher_prometheus',
        )
        self.fetcher = prometheus.PrometheusFetcher()

    def test_get_tenants_build_query(self):
        query = (
            'max(http_requests_total) by (namespace)'
        )

        with mock.patch.object(
            PrometheusClient, 'get_instant',
        ) as mock_get:
            self.fetcher.get_tenants()
            mock_get.assert_called_once_with(query)

    def test_get_tenants_build_query_with_filter(self):
        query = (
            'max(http_requests_total{label1="foo"})'
            ' by (namespace)'
        )

        self.conf.set_override(
            'filters', 'label1:foo', 'fetcher_prometheus',
        )

        with mock.patch.object(
            PrometheusClient, 'get_instant',
        ) as mock_get:
            self.fetcher.get_tenants()
            mock_get.assert_called_once_with(query)

    def test_get_tenants(self):
        response = mock.patch(
            'cloudkitty.common.prometheus_client.PrometheusClient.get_instant',
            return_value={
                'data': {
                    'result': [
                        {
                            'metric': {},
                            'value': [42, 1337],
                        },
                        {
                            'metric': {'namespace': 'scope_id1'},
                            'value': [42, 1337],
                        },
                        {
                            'metric': {'namespace': 'scope_id2'},
                            'value': [42, 1337],
                        },
                        {
                            'metric': {'namespace': 'scope_id3'},
                            'value': [42, 1337],
                        },
                    ]
                }
            },
        )

        with response:
            scopes = self.fetcher.get_tenants()
            self.assertCountEqual(scopes, [
                'scope_id1', 'scope_id2', 'scope_id3',
            ])

    def test_get_tenants_raises_exception(self):
        no_response = mock.patch(
            'cloudkitty.common.prometheus_client.PrometheusClient.get_instant',
            return_value={},
        )

        with no_response:
            self.assertRaises(
                prometheus.PrometheusFetcherError,
                self.fetcher.get_tenants,
            )

    def test_get_tenants_raises_exception2(self):
        invalid_response = mock.patch(
            'cloudkitty.common.prometheus_client.PrometheusClient.get_instant',
            side_effect=PrometheusResponseError,
        )

        with invalid_response:
            self.assertRaises(
                prometheus.PrometheusFetcherError,
                self.fetcher.get_tenants,
            )
