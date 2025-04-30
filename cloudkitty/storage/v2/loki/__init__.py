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
import datetime
import json

from oslo_config import cfg
from oslo_log import log as oslo_logging

from cloudkitty import dataframe
from cloudkitty.storage import v2 as v2_storage
from cloudkitty.storage.v2.loki import client as os_client
from cloudkitty.utils import tz as tzutils

LOG = oslo_logging.getLogger(__name__)

CONF = cfg.CONF

LOKI_STORAGE_GROUP = 'storage_loki'

loki_storage_opts = [
    cfg.StrOpt(
        'url',
        help='Loki base url. Defaults to '
             'http://localhost:3100/loki/api/v1',
        default='http://localhost:3100/loki/api/v1'),
    cfg.StrOpt(
        'tenant',
        help='The loki tenant to be used. Defaults to tenant1.',
        default='tenant1'),
    cfg.DictOpt(
        'stream',
        help='The labels that are going to be used to define the Loki stream '
             'as Python dict. Defaults to {"service": "cloudkitty"}.',
        default={"service": "cloudkitty"}),
    cfg.IntOpt(
        'buffer_size',
        help='The number of messages that will be grouped together before '
             'launching a Loki HTTP POST request.',
        default=1),
    cfg.StrOpt(
        'content_type',
        help='The http Content-Type that will be used to send info to Loki. '
             'Defaults to application/json. It can also be '
             'application/x-protobuf',
        default='application/json'),
    cfg.BoolOpt(
        'insecure',
        help='Set to true to allow insecure HTTPS connections to Loki',
        default=False),
    cfg.StrOpt(
        'cafile',
        help='Path of the CA certificate to trust for HTTPS connections.',
        default=None)
]

CONF.register_opts(loki_storage_opts, LOKI_STORAGE_GROUP)


class LokiStorage(v2_storage.BaseStorage):

    def __init__(self, *args, **kwargs):
        super(LokiStorage, self).__init__(*args, **kwargs)

        verify = not CONF.storage_loki.insecure
        if verify and CONF.storage_loki.cafile:
            verify = CONF.storage_loki.cafile

        self._conn = os_client.LokiClient(
            CONF.storage_loki.url,
            CONF.storage_loki.tenant,
            CONF.storage_loki.stream,
            CONF.storage_loki.content_type,
            CONF.storage_loki.buffer_size)

    def init(self):
        LOG.debug('LokiStorage Init.')

    def push(self, dataframes, scope_id=None):
        for frame in dataframes:
            for type_, point in frame.iterpoints():
                start, end = self._local_to_utc(frame.start, frame.end)
                self._conn.add_point(point, type_, start, end)

    @staticmethod
    def _local_to_utc(*args):
        return [tzutils.local_to_utc(arg) for arg in args]

    @staticmethod
    def _log_to_datapoint(labels):
        return dataframe.DataPoint(
            labels['unit'],
            labels['qty'],
            labels['price'],
            labels['groupby'],
            labels['metadata'],
        )

    def _build_dataframes(self, logs):
        dataframes = {}
        for log in logs:
            labels = json.loads(log['values'][0][1])
            start = tzutils.dt_from_iso(labels['start'])
            end = tzutils.dt_from_iso(labels['end'])
            key = (start, end)
            if key not in dataframes.keys():
                dataframes[key] = dataframe.DataFrame(start=start, end=end)
            dataframes[key].add_point(
                self._log_to_datapoint(labels), labels['type'])

        output = list(dataframes.values())
        output.sort(key=lambda frame: (frame.start, frame.end))
        return output

    def retrieve(self, begin=None, end=None,
                 filters=None,
                 metric_types=None,
                 offset=0, limit=1000, paginate=True):
        begin, end = self._local_to_utc(begin or tzutils.get_month_start(),
                                        end or tzutils.get_next_month())
        total, logs = self._conn.retrieve(
            begin, end, filters, metric_types, limit)
        dataframes = self._build_dataframes(logs)
        return {
            'total': total,
            'dataframes': dataframes
        }

    def delete(self, begin=None, end=None, filters=None):
        self._conn.delete(begin, end, filters)

    @staticmethod
    def _normalize_time(t):
        if isinstance(t, datetime.datetime):
            return tzutils.utc_to_local(t)
        return tzutils.dt_from_iso(t)

    def _doc_to_total_result(self, doc, start, end):
        output = {
            'begin': self._normalize_time(doc.get('start', start)),
            'end': self._normalize_time(doc.get('end', end)),
            'qty': doc['sum_qty']['value'],
            'rate': doc['sum_price']['value'],
        }
        if 'key' in doc.keys():
            for key, value in doc['key'].items():
                output[key] = value
        return output

    def total(self, groupby=None, begin=None, end=None, metric_types=None,
              filters=None, custom_fields=None, offset=0, limit=1000,
              paginate=False):
        begin, end = self._local_to_utc(begin or tzutils.get_month_start(),
                                        end or tzutils.get_next_month())

        total, docs = self._conn.total(begin, end, metric_types, filters,
                                       groupby, custom_fields=custom_fields,
                                       offset=offset, limit=limit,
                                       paginate=False)
        results = [
            self._doc_to_total_result(doc, begin, end) for doc in docs
        ]

        return {
            'total': total,
            'results': results,
        }
