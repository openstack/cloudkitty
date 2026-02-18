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
from decimal import Decimal
from unittest import mock

from cloudkitty.collector import aetos
from cloudkitty.collector import exceptions
from cloudkitty.common import prometheus_client_base
from cloudkitty import tests
from cloudkitty.tests import samples


class AetosCollectorTest(tests.TestCase):
    def setUp(self):
        super(AetosCollectorTest, self).setUp()
        self._tenant_id = samples.TENANT

        # Set up config overrides
        self.conf.set_override('interface', 'public', 'collector_aetos')
        self.conf.set_override('region_name', 'RegionOne', 'collector_aetos')

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

        # Mock keystoneauth1 and session creation
        self.mock_auth_patch = mock.patch(
            'cloudkitty.collector.aetos.ks_loading.'
            'load_auth_from_conf_options',
            return_value=mock.Mock()
        )
        self.mock_session_patch = mock.patch(
            'cloudkitty.collector.aetos.ks_loading.'
            'load_session_from_conf_options',
            return_value=mock.Mock()
        )
        self.mock_aetos_client_patch = mock.patch(
            'cloudkitty.collector.aetos.aetos_client.AetosClient'
        )

        self.mock_auth = self.mock_auth_patch.start()
        self.mock_session = self.mock_session_patch.start()
        self.mock_aetos_client = self.mock_aetos_client_patch.start()

        self.addCleanup(self.mock_auth_patch.stop)
        self.addCleanup(self.mock_session_patch.stop)
        self.addCleanup(self.mock_aetos_client_patch.stop)

        self.collector = aetos.AetosCollector(**args)

    def test_init(self):
        """Test AetosCollector initialization."""
        # Verify collector name is set
        self.assertEqual(self.collector.collector_name, 'aetos')

        # Verify auth loading was called
        self.assertTrue(self.mock_auth.called)

        # Verify session creation was called
        self.assertTrue(self.mock_session.called)

        # Verify AetosClient was instantiated
        self.assertTrue(self.mock_aetos_client.called)

    def test_fetch_all_build_query(self):
        """Test that fetch_all builds correct query."""
        query = (
            'avg(avg_over_time(http_requests_total'
            '{project_id="f266f30b11f246b589fd266f85eeec39"}[3600s]'
            ')) by (foo, bar, project_id, code, instance)'
        )

        # Mock the _conn.get_instant method
        mock_client_instance = self.mock_aetos_client.return_value
        mock_client_instance.get_instant.return_value = {
            'status': 'success',
            'data': {'result': []}
        }

        # Call fetch_all
        self.collector.fetch_all(
            'http_requests_total',
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id,
        )

        # Verify get_instant was called with correct query
        mock_client_instance.get_instant.assert_called_once_with(
            query,
            samples.FIRST_PERIOD_END.isoformat(),
        )

    def test_format_data_instant_query(self):
        """Test data formatting from Prometheus response."""
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

    def test_fetch_all_with_error_response(self):
        """Test that fetch_all raises CollectError on Prometheus error."""
        # Mock the _conn.get_instant to return error response
        mock_client_instance = self.mock_aetos_client.return_value
        mock_client_instance.get_instant.return_value = {
            'status': 'error',
            'errorType': 'bad_data',
            'error': 'invalid PromQL'
        }

        # Verify CollectError is raised
        self.assertRaises(
            exceptions.CollectError,
            self.collector.fetch_all,
            'http_requests_total',
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id,
        )

    def test_fetch_all_with_client_exception(self):
        """Test that fetch_all raises CollectError on client exception."""
        # Mock the _conn.get_instant to raise PrometheusResponseError
        mock_client_instance = self.mock_aetos_client.return_value
        mock_client_instance.get_instant.side_effect = \
            prometheus_client_base.PrometheusResponseError(
                'Connection failed'
            )

        # Verify CollectError is raised
        self.assertRaises(
            exceptions.CollectError,
            self.collector.fetch_all,
            'http_requests_total',
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id,
        )

    def test_fetch_all_empty_result(self):
        """Test that fetch_all returns empty list for empty result."""
        # Mock empty result
        mock_client_instance = self.mock_aetos_client.return_value
        mock_client_instance.get_instant.return_value = {
            'status': 'success',
            'data': {'result': []}
        }

        result = self.collector.fetch_all(
            'http_requests_total',
            samples.FIRST_PERIOD_BEGIN,
            samples.FIRST_PERIOD_END,
            self._tenant_id,
        )

        self.assertEqual(result, [])

    def test_check_configuration(self):
        """Test configuration validation."""
        conf = {
            'metrics': {
                'test_metric': {
                    'unit': 'instance',
                    'groupby': ['project_id'],
                    'metadata': ['code'],
                    'extra_args': {
                        'aggregation_method': 'max',
                        'query_function': 'abs',
                    }
                }
            }
        }

        # Should not raise an error
        validated = aetos.AetosCollector.check_configuration(conf)
        self.assertIn('test_metric', validated)
        self.assertEqual(
            validated['test_metric']['extra_args']['aggregation_method'],
            'max'
        )
