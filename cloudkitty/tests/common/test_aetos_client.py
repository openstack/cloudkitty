# Copyright 2026 Red Hat, Inc.
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

from observabilityclient import prometheus_client

from cloudkitty.common import aetos_client
from cloudkitty.common import prometheus_client_base
from cloudkitty import tests


class AetosClientTest(tests.TestCase):

    def setUp(self):
        super(AetosClientTest, self).setUp()
        # Mock the observabilityclient
        self.mock_prom_client = mock.Mock()
        self.mock_get_client = mock.patch(
            'cloudkitty.common.aetos_client.obs_client_utils.'
            'get_prom_client_from_keystone',
            return_value=self.mock_prom_client
        )
        self.mock_get_client.start()
        self.addCleanup(self.mock_get_client.stop)

        # Create client with mock session
        self.mock_session = mock.Mock()
        self.adapter_options = {
            'interface': 'public',
            'region_name': 'RegionOne',
            'service_type': 'metric-storage',
        }
        self.client = aetos_client.AetosClient(
            self.mock_session,
            self.adapter_options
        )

    def test_init(self):
        """Test AetosClient initialization."""
        # Verify get_prom_client_from_keystone was called with correct args
        mock_call = self.mock_get_client.call_args
        self.assertEqual(mock_call[0][0], self.mock_session)
        self.assertEqual(
            mock_call[1]['adapter_options'],
            self.adapter_options
        )

    def test_get_instant_success(self):
        """Test successful instant query."""
        # Mock the observabilityclient response
        self.mock_prom_client._get.return_value = {
            'status': 'success',
            'data': {
                'result': [
                    {
                        'metric': {'project_id': 'test'},
                        'value': [1234567890, '42']
                    }
                ]
            }
        }

        # Execute query
        result = self.client.get_instant(
            'http_requests_total',
            time='2024-01-01T00:00:00Z',
            timeout='30s'
        )

        # Verify observabilityclient was called correctly
        self.mock_prom_client._get.assert_called_once_with(
            'query',
            params={
                'query': 'http_requests_total',
                'time': '2024-01-01T00:00:00Z',
                'timeout': '30s'
            }
        )

        # Verify result
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['data']['result']), 1)

    def test_get_instant_with_no_time_timeout(self):
        """Test instant query without time and timeout."""
        self.mock_prom_client._get.return_value = {
            'status': 'success',
            'data': {'result': []}
        }

        result = self.client.get_instant('test_metric')

        self.mock_prom_client._get.assert_called_once_with(
            'query',
            params={
                'query': 'test_metric',
                'time': None,
                'timeout': None
            }
        )
        self.assertEqual(result['status'], 'success')

    def test_get_instant_raises_error_on_exception(self):
        """observabilityclient exception raises PrometheusResponseError."""
        # Mock observabilityclient to raise exception
        self.mock_prom_client._get.side_effect = \
            prometheus_client.PrometheusAPIClientError(
                'Invalid query'
            )

        # Verify PrometheusResponseError is raised
        self.assertRaises(
            prometheus_client_base.PrometheusResponseError,
            self.client.get_instant,
            'bad_query'
        )
