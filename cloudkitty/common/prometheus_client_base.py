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
import abc


class PrometheusResponseError(Exception):
    pass


class PrometheusClientBase(metaclass=abc.ABCMeta):
    """Abstract base class for Prometheus-compatible clients.

    This class defines the interface that all Prometheus-compatible clients
    must implement. Subclasses should implement the _get and get_instant
    methods to handle communication with Prometheus or Prometheus-compatible
    APIs (such as Aetos).
    """

    INSTANT_QUERY_ENDPOINT = 'query'
    RANGE_QUERY_ENDPOINT = 'query_range'

    @abc.abstractmethod
    def _get(self, endpoint, params):
        """Execute GET request to Prometheus API.

        :param endpoint: API endpoint (e.g., 'query', 'query_range')
        :param params: Query parameters dict
        :return: HTTP response object with .json() method
        """
        pass

    @abc.abstractmethod
    def get_instant(self, query, time=None, timeout=None):
        """Execute instant query against Prometheus API.

        :param query: PromQL query string
        :param time: Evaluation timestamp (ISO format string)
        :param timeout: Query timeout
        :return: JSON response dict
        :raises: PrometheusResponseError on invalid JSON
        """
        pass
