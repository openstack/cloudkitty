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
from datetime import datetime
from datetime import timezone

from cloudkitty.storage.v2.loki import client as loki_client_module
from cloudkitty.storage.v2.loki import exceptions as loki_exceptions
from cloudkitty.utils import json


class FakeLokiClient(loki_client_module.LokiClient):

    def __init__(self, url, tenant, stream_labels, content_type,
                 buffer_size, **kwargs):
        if content_type != "application/json":
            raise loki_exceptions.UnsupportedContentType(content_type)

        self._base_url = url.strip('/') if url else 'http://fake-loki'
        self._stream_labels = stream_labels if stream_labels \
            else {"fake_label": "fake_value"}
        self._headers = {
            'X-Scope-OrgID': tenant,
            'Content-Type': content_type
        }
        self._buffer_size = buffer_size

        self._logs = []
        self.init()

    def init(self):
        self._logs = []

    def add_point(self, point, type, start, end):
        loki_timestamp_ns_str = str(
            int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
        )

        data_to_log = {
            'start': start,
            'end': end,
            'type': type,
            'unit': point.unit,
            'description': point.description,
            'qty': point.qty,
            'price': point.price,
            'groupby': point.groupby,
            'metadata': point.metadata
        }

        flattened_stream = {
            "stream": {
                    'detected_level': 'unknown',
                    'start': start,
                    'end': end,
                    'groupby_day_of_the_year': data_to_log.get('groupby').
                    get('day_of_the_year'),
                    'groupby_id': data_to_log.get('groupby').get('id'),
                    'groupby_month': data_to_log.get('groupby').get('month'),
                    'groupby_project_id': data_to_log.get('groupby').
                    get('project_id'),
                    'groupby_user_id': data_to_log.get('groupby').
                    get('user_id'),
                    'groupby_week_of_the_year': data_to_log.get('groupby').
                    get('week_of_the_year'),
                    'groupby_year': data_to_log.get('groupby').
                    get('year'),
                    'metadata_flavor_id': data_to_log.get('metadata').
                    get('flavor_id'),
                    'metadata_flavor_name': data_to_log.get('metadata').
                    get('flavor_name'),
                    'metadata_vcpus': data_to_log.get('metadata').
                    get('vcpus'),
                    'price': data_to_log.get('price'),
                    'qty': data_to_log.get('qty'),
                    'type': data_to_log.get('type'),
                    'unit': data_to_log.get('unit')
            },
            "values": [
                [loki_timestamp_ns_str, json.dumps(data_to_log)]
            ]
        }

        self._logs.append(flattened_stream)

    def push(self):
        pass

    def __filter_func(self, begin, end, filters, mtypes):
        matched_points = []
        for log in self._logs:
            stream = log.get('stream')

            if begin and stream.get('start') < begin:
                continue
            if end and stream.get('start') >= end:
                continue

            if mtypes and stream.get('type') not in mtypes:
                continue

            filter_match_passes = True
            if filters:
                for key, value in filters.items():
                    if stream.get('groupby_' + key) != value:
                        filter_match_passes = False
                        break
            if not filter_match_passes:
                continue

            matched_points.append(log)
        return matched_points

    def retrieve(self, begin, end, filters, metric_types, limit):
        points = self.__filter_func(begin, end, filters, metric_types)

        total = len(points)

        if limit > 0:
            effective_limit = limit
        else:
            effective_limit = 1000

        output = points[:effective_limit]

        if not output:
            return 0, []

        return total, output

    def total(self, begin, end, metric_types, filters, groupby,
              custom_fields=None, offset=0, limit=1000, paginate=True):
        data = self.__filter_func(begin, end, filters, metric_types)

        if not data:
            if not groupby:
                return 1, [{'sum_qty': {'value': 0.0},
                            'sum_price': {'value': 0.0}}]
            else:
                return 0, []

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

        if limit <= 0:
            paginated_results = result[offset:]
        else:
            paginated_results = result[offset: offset + limit]

        return len(result), paginated_results
