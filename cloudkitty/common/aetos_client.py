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
from observabilityclient import prometheus_client
from observabilityclient.utils import metric_utils as obs_client_utils

from cloudkitty.common import prometheus_client_base


class AetosClient(prometheus_client_base.PrometheusClientBase):
    """Aetos client using Keystone authentication.

    This client uses python-observabilityclient to access Prometheus
    metrics through the Aetos reverse-proxy with Keystone authentication.
    """

    def __init__(self, session, adapter_options):
        """Initialize Aetos client.

        :param session: Keystoneauth1 session with valid authentication
        :param adapter_options: Dict with options for the keystoneauth1
                                adapter
        """
        self._client = obs_client_utils.get_prom_client_from_keystone(
            session, adapter_options=adapter_options
        )

    def _get(self, endpoint, params):
        """Execute GET request against Aetos via observabilityclient.

        :param endpoint: API endpoint ('query' or 'query_range')
        :param params: Query parameters
        :return: Prometheus response json as dict
        """
        # NOTE(jwysogla): The following line uses a "private" _get()
        # from the python-observabilityclient. This is intentional. This
        # function provides a lower level communication more similar
        # to what the PrometheusClient is doing. Using this function
        # became a pattern, it's heavily used by Aodh, Watcher and Aetos as
        # well and it's usage by services is well known to
        # python-observabilityclient maintainers.
        result = self._client._get(endpoint, params)
        return result

    def get_instant(self, query, time=None, timeout=None):
        """Execute instant query against Aetos.

        :param query: PromQL query string
        :param time: Evaluation timestamp (ISO format)
        :param timeout: Query timeout
        :return: JSON response dict
        :raises: PrometheusResponseError on invalid response
        """
        try:
            res = self._get(
                self.INSTANT_QUERY_ENDPOINT,
                params={'query': query, 'time': time, 'timeout': timeout},
            )
            return res
        except prometheus_client.PrometheusAPIClientError as e:
            raise prometheus_client_base.PrometheusResponseError(
                'Could not get a valid json response for '
                'query {} (error: {})'.format(query, e)
            )
