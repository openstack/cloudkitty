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
import requests


class PrometheusResponseError(Exception):
    pass


class PrometheusClient(object):
    INSTANT_QUERY_ENDPOINT = 'query'
    RANGE_QUERY_ENDPOINT = 'query_range'

    def __init__(self, url, auth=None, verify=True):
        self.url = url
        self.auth = auth
        self.verify = verify

    def _get(self, endpoint, params):
        return requests.get(
            '{}/{}'.format(self.url, endpoint),
            params=params,
            auth=self.auth,
            verify=self.verify,
        )

    def get_instant(self, query, time=None, timeout=None):
        res = self._get(
            self.INSTANT_QUERY_ENDPOINT,
            params={'query': query, 'time': time, 'timeout': timeout},
        )
        try:
            return res.json()
        except ValueError:
            raise PrometheusResponseError(
                'Could not get a valid json response for '
                '{} (response: {})'.format(res.url, res.text)
            )

    def get_range(self, query, start, end, step, timeout=None):
        res = self._get(
            self.RANGE_QUERY_ENDPOINT,
            params={
                'query': query,
                'start': start,
                'end': end,
                'step': step,
                'timeout': timeout,
            },
        )
        try:
            return res.json()
        except ValueError:
            raise PrometheusResponseError(
                'Could not get a valid json response for '
                '{} (response: {})'.format(res.url, res.text)
            )
