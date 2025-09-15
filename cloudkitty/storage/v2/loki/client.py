# Copyright 2025 Red Hat
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
from oslo_log import log
import requests

from cloudkitty.storage.v2.loki import exceptions
from cloudkitty.utils import json

LOG = log.getLogger(__name__)


class LokiClient(object):
    """Class used to ease interaction with Loki."""

    def __init__(self, url, tenant, stream_labels, content_type, buffer_size,
                 cert, verify):
        if content_type != "application/json":
            raise exceptions.UnsupportedContentType(content_type)

        self._base_url = url.strip('/')
        self._stream_labels = stream_labels
        self._headers = {
            'X-Scope-OrgID': tenant,
            'Content-Type': content_type
        }
        self._buffer_size = buffer_size
        self._points = []

        self._cert = cert
        self._verify = verify

    def _build_payload_json(self, batch):
        payload = {
            "streams": [
                {
                    "stream": self._stream_labels,
                    "values": batch
                }
            ]
        }
        return payload

    def _dict_to_loki_query(self, tags_dict, groupby=False, brackets=True):
        """Converts from Python dict to Loki query language."""
        if not tags_dict:
            return '{}'

        pairs = []
        for key, value in tags_dict.items():
            if isinstance(value, list):
                value = value[0]
            if isinstance(value, str):
                value = value.replace('"', '\\"')
            if groupby:
                pairs.append(f'groupby_{key}="{value}"')
            else:
                pairs.append(f'{key}="{value}"')

        if brackets:
            return '{' + ', '.join(pairs) + '}'
        else:
            return ', '.join(pairs)

    def _base_query(self):
        """Makes sure that we always get json results."""
        return self._dict_to_loki_query(self._stream_labels) + ' | json'

    def search(self, query, begin, end, limit):
        url = f"{self._base_url}/query_range"

        if query is None:
            query = self._base_query()

        params = {
            "query": query,
            "start": int(begin.timestamp() * 1_000_000_000),
            "end": int(end.timestamp() * 1_000_000_000),
            "limit": limit
        }

        response = requests.get(url, params=params, headers=self._headers,
                                cert=self._cert, verify=self._verify)

        if response.status_code == 200:
            data = response.json()['data']
        else:
            msg = (f"Failed to query logs or empty result: "
                   f"{response.status_code} - {response.text}")
            LOG.error(msg)
            data = []
        return data

    def push(self):
        """Send messages to Loki in batches."""
        url = f"{self._base_url}/push"

        while self._points:
            payload = self._build_payload_json(self._points)
            response = requests.post(url, json=payload, headers=self._headers,
                                     cert=self._cert, verify=self._verify)

            if response.status_code == 204:
                LOG.debug(
                    f"Batch of {len(self._points)} messages pushed "
                    f"successfully."
                )
                self._points = []
            else:
                LOG.error(
                    f"Failed to push logs: {response.status_code} - "
                    f"{response.text}"
                )
                break

    def delete_by_query(self, query, begin, end):
        url = f"{self._base_url}/delete"

        if query is None:
            query = self._base_query()

        params = {
            "query": query,
            "start": int(begin.timestamp()),
            "end": int(end.timestamp()),
        }

        response = requests.post(url, params=params, headers=self._headers,
                                 cert=self._cert, verify=self._verify)

        if response.status_code == 204:
            LOG.debug(
                "Dataframes deleted successfully."
            )
        else:
            LOG.error(
                f"Failed to delete dataframes: {response.status_code} - "
                f"{response.text}"
            )

    def delete(self, begin, end, filters):
        query = self._base_query()
        loki_query_parts = []
        if filters:
            loki_query_parts.append(
                self._dict_to_loki_query(
                    filters, groupby=True, brackets=False
                )
            )

        if loki_query_parts:
            query += ' | ' + ', '.join(loki_query_parts)

        self.delete_by_query(query, begin, end)

    def retrieve(self, begin, end, filters, metric_types, limit):
        """Retrieves dataframes stored in Loki."""
        query = self._base_query()
        loki_query_parts = []

        if filters:
            loki_query_parts.append(
                self._dict_to_loki_query(
                    filters, groupby=True, brackets=False
                )
            )

        if metric_types:
            if isinstance(metric_types, list):
                current_metric_type = metric_types[0]
            else:
                current_metric_type = metric_types
            loki_query_parts.append(f'type = "{current_metric_type}"')

        if loki_query_parts:
            query += ' | ' + ', '.join(loki_query_parts)

        data_response = self.search(query, begin, end, limit)

        if not isinstance(data_response, dict) or \
           'stats' not in data_response or \
           'result' not in data_response:
            LOG.warning(
                f"Data from Loki search is not in the expected dictionary "
                f"format or is missing keys. Query: '{query}'. Response "
                f"received: {data_response}"
            )
            return 0, []

        total = data_response.get('stats', {})\
            .get('summary', {})\
            .get('totalEntriesReturned', 0)
        output = data_response.get('result', [])

        return total, output

    def add_point(self, point, type, start, end):
        """Append a point to the client."""
        timestamp_ns = int(end.timestamp() * 1_000_000_000)
        timestamp = str(timestamp_ns)

        data = {
            'start': start,
            'end': end,
            'type': type,
            'unit': point.unit,
            'description': point.description,
            'qty': point.qty,
            'price': point.price,
            'groupby': point.groupby,
            'metadata': point.metadata,
        }

        log_line = json.dumps(data)
        self._points.append([timestamp, log_line])

        if len(self._points) >= self._buffer_size:
            self.push()

    def total(self, begin, end, metric_types, filters, groupby,
              custom_fields, offset, limit, paginate):
        """Calculate total sum of 'price' and 'qty' for entries.

        This method calculates totals for entries that match the specified
        groupby value.
        """
        if custom_fields:
            LOG.warning(
                "'custom_fields' are not implemented yet for Loki. "
                "Therefore, the custom fields [%s] informed by the user "
                "will be ignored.", custom_fields
            )

        if offset != 0:
            LOG.warning("offset is not supported by Loki.")

        total_count, data = self.retrieve(
            begin, end, filters, metric_types, limit
        )

        if not groupby:
            total_qty = 0.0
            total_price = 0.0
            for item in data:
                stream = item.get('stream', {})
                qty = float(stream.get('qty', 0))
                price = float(stream.get('price', 0))

                total_qty += qty
                total_price += price

            return 1, [{
                'sum_qty': {'value': total_qty},
                'sum_price': {'value': total_price}
            }]

        grouped_data = {}
        for item in data:
            stream = item.get('stream', {})
            qty = float(stream.get('qty', 0))
            price = float(stream.get('price', 0))

            key_parts = {}
            for field in groupby:
                if field == 'type':
                    key_parts[field] = stream.get(field, '')
                else:
                    key_parts[field] = stream.get('groupby_' + field)

            key = tuple((k, v) for k, v in sorted(key_parts.items()))

            if key not in grouped_data:
                grouped_data[key] = {
                    'sum_qty': 0.0,
                    'sum_price': 0.0,
                    'key_parts': dict(key_parts)
                }

            grouped_data[key]['sum_qty'] += qty
            grouped_data[key]['sum_price'] += price

        result = []
        for _key_tuple, values in grouped_data.items():
            result.append({
                'key': values['key_parts'],
                'sum_qty': {'value': values['sum_qty']},
                'sum_price': {'value': values['sum_price']}
            })
        return len(result), result
