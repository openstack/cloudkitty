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
import datetime

from oslo_config import cfg
from oslo_log import log

from cloudkitty import dataframe
from cloudkitty.storage import v2 as v2_storage
from cloudkitty.storage.v2.elasticsearch import client as es_client
from cloudkitty.storage.v2.elasticsearch import exceptions
from cloudkitty.utils import tz as tzutils

LOG = log.getLogger(__name__)

CONF = cfg.CONF

ELASTICSEARCH_STORAGE_GROUP = 'storage_elasticsearch'

elasticsearch_storage_opts = [
    cfg.StrOpt(
        'host',
        help='Elasticsearch host, along with port and protocol. '
             'Defaults to http://localhost:9200',
        default='http://localhost:9200'),
    cfg.StrOpt(
        'index_name',
        help='Elasticsearch index to use. Defaults to "cloudkitty".',
        default='cloudkitty'),
    cfg.BoolOpt('insecure',
                help='Set to true to allow insecure HTTPS '
                     'connections to Elasticsearch',
                default=False),
    cfg.StrOpt('cafile',
               help='Path of the CA certificate to trust for '
                    'HTTPS connections.',
               default=None),
    cfg.IntOpt('scroll_duration',
               help="Duration (in seconds) for which the ES scroll contexts "
                    "should be kept alive.",
               advanced=True,
               default=30, min=0, max=300),
]

CONF.register_opts(elasticsearch_storage_opts, ELASTICSEARCH_STORAGE_GROUP)

CLOUDKITTY_INDEX_MAPPING = {
    "dynamic_templates": [
        {
            "strings_as_keywords": {
                "match_mapping_type": "string",
                "mapping": {
                    "type": "keyword"
                }
            }
        }
    ],
    "dynamic": False,
    "properties": {
        "start": {"type": "date"},
        "end": {"type": "date"},
        "type": {"type": "keyword"},
        "unit": {"type": "keyword"},
        "qty": {"type": "double"},
        "price": {"type": "double"},
        "groupby": {"dynamic": True, "type": "object"},
        "metadata": {"dynamic": True, "type": "object"}
    },
}


class ElasticsearchStorage(v2_storage.BaseStorage):

    def __init__(self, *args, **kwargs):
        super(ElasticsearchStorage, self).__init__(*args, **kwargs)

        verify = not CONF.storage_elasticsearch.insecure
        if verify and CONF.storage_elasticsearch.cafile:
            verify = CONF.storage_elasticsearch.cafile

        self._conn = es_client.ElasticsearchClient(
            CONF.storage_elasticsearch.host,
            CONF.storage_elasticsearch.index_name,
            "_doc",
            verify=verify)

    def init(self):
        r = self._conn.get_index()
        if r.status_code != 200:
            raise exceptions.IndexDoesNotExist(
                CONF.storage_elasticsearch.index_name)
        LOG.info('Creating mapping "_doc" on index {}...'.format(
            CONF.storage_elasticsearch.index_name))
        self._conn.put_mapping(CLOUDKITTY_INDEX_MAPPING)
        LOG.info('Mapping created.')

    def push(self, dataframes, scope_id=None):
        for frame in dataframes:
            for type_, point in frame.iterpoints():
                start, end = self._local_to_utc(frame.start, frame.end)
                self._conn.add_point(point, type_, start, end)

        self._conn.commit()

    @staticmethod
    def _local_to_utc(*args):
        return [tzutils.local_to_utc(arg) for arg in args]

    @staticmethod
    def _doc_to_datapoint(doc):
        return dataframe.DataPoint(
            doc['unit'],
            doc['qty'],
            doc['price'],
            doc['groupby'],
            doc['metadata'],
        )

    def _build_dataframes(self, docs):
        dataframes = {}
        nb_points = 0
        for doc in docs:
            source = doc['_source']
            start = tzutils.dt_from_iso(source['start'])
            end = tzutils.dt_from_iso(source['end'])
            key = (start, end)
            if key not in dataframes.keys():
                dataframes[key] = dataframe.DataFrame(start=start, end=end)
            dataframes[key].add_point(
                self._doc_to_datapoint(source), source['type'])
            nb_points += 1

        output = list(dataframes.values())
        output.sort(key=lambda frame: (frame.start, frame.end))
        return output

    def retrieve(self, begin=None, end=None,
                 filters=None,
                 metric_types=None,
                 offset=0, limit=1000, paginate=True):
        begin, end = self._local_to_utc(begin or tzutils.get_month_start(),
                                        end or tzutils.get_next_month())
        total, docs = self._conn.retrieve(
            begin, end, filters, metric_types,
            offset=offset, limit=limit, paginate=paginate)
        return {
            'total': total,
            'dataframes': self._build_dataframes(docs),
        }

    def delete(self, begin=None, end=None, filters=None):
        self._conn.delete_by_query(begin, end, filters)

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
        # Means we had a composite aggregation
        if 'key' in doc.keys():
            for key, value in doc['key'].items():
                if key == 'begin' or key == 'end':
                    # Elasticsearch returns ts in milliseconds
                    value = tzutils.dt_from_ts(value // 1000)
                output[key] = value
        return output

    def total(self, groupby=None, begin=None, end=None, metric_types=None,
              filters=None, custom_fields=None, offset=0, limit=1000,
              paginate=True):
        begin, end = self._local_to_utc(begin or tzutils.get_month_start(),
                                        end or tzutils.get_next_month())

        groupby = self.parse_groupby_syntax_to_groupby_elements(groupby)
        total, docs = self._conn.total(begin, end, metric_types, filters,
                                       groupby, custom_fields=custom_fields,
                                       offset=offset, limit=limit,
                                       paginate=paginate)
        return {
            'total': total,
            'results': [self._doc_to_total_result(doc, begin, end)
                        for doc in docs],
        }
