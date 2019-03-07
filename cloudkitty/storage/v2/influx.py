# Copyright 2018 Objectif Libre
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
# @author: Luka Peschke
#
import copy
import datetime
import decimal

import influxdb
from oslo_config import cfg
from oslo_log import log
import six

from cloudkitty.storage import v2 as v2_storage
from cloudkitty import utils


LOG = log.getLogger(__name__)


CONF = cfg.CONF
CONF.import_opt('period', 'cloudkitty.collector', 'collect')

INFLUX_STORAGE_GROUP = 'storage_influxdb'

influx_storage_opts = [
    cfg.StrOpt('username', help='InfluxDB username'),
    cfg.StrOpt('password', help='InfluxDB password', secret=True),
    cfg.StrOpt('database', help='InfluxDB database'),
    cfg.StrOpt('retention_policy', default='autogen',
               help='Retention policy to use'),
    cfg.StrOpt('host', help='InfluxDB host', default='localhost'),
    cfg.IntOpt('port', help='InfluxDB port', default=8086),
    cfg.BoolOpt(
        'use_ssl',
        help='Set to true to use ssl for influxDB connection. '
        'Defaults to False',
        default=False,
    ),
    cfg.BoolOpt(
        'insecure',
        help='Set to true to authorize insecure HTTPS connections to '
        'influxDB. Defaults to False',
        default=False,
    ),
    cfg.StrOpt(
        'cafile',
        help='Path of the CA certificate to trust for HTTPS connections',
        default=None
    ),
]

CONF.register_opts(influx_storage_opts, INFLUX_STORAGE_GROUP)


class InfluxClient(object):
    """Classe used to ease interaction with InfluxDB"""

    def __init__(self, chunk_size=500, autocommit=True):
        """Creates an InfluxClient object.

        :param chunk_size: Size after which points should be pushed.
        :param autocommit: Set to false to disable autocommit
        """
        self._conn = self._get_influx_client()
        self._chunk_size = chunk_size
        self._autocommit = autocommit
        self._retention_policy = CONF.storage_influxdb.retention_policy
        self._points = []

    @staticmethod
    def _get_influx_client():
        verify = CONF.storage_influxdb.use_ssl and not \
            CONF.storage_influxdb.insecure

        if verify and CONF.storage_influxdb.cafile:
            verify = CONF.storage_influxdb.cafile

        return influxdb.InfluxDBClient(
            username=CONF.storage_influxdb.username,
            password=CONF.storage_influxdb.password,
            host=CONF.storage_influxdb.host,
            port=CONF.storage_influxdb.port,
            database=CONF.storage_influxdb.database,
            ssl=CONF.storage_influxdb.use_ssl,
            verify_ssl=verify,
        )

    def retention_policy_exists(self, database, policy):
        policies = self._conn.get_list_retention_policies(database)
        return policy in [pol['name'] for pol in policies]

    def commit(self):
        total_points = len(self._points)
        if len(self._points) < 1:
            return
        LOG.debug('Pushing {} points to InfluxDB'.format(total_points))
        self._conn.write_points(self._points,
                                retention_policy=self._retention_policy)
        self._points = []

    def append_point(self,
                     metric_type,
                     timestamp,
                     qty, price, unit,
                     fields, tags):
        """Adds two points to commit to InfluxDB"""

        measurement_fields = copy.deepcopy(fields)
        measurement_fields['qty'] = float(qty)
        measurement_fields['price'] = float(price)
        measurement_fields['unit'] = unit
        # Unfortunately, this seems to be the fastest way: Having several
        # measurements would imply a high client-side workload, and this allows
        # us to filter out unrequired keys
        measurement_fields['groupby'] = '|'.join(tags.keys())
        measurement_fields['metadata'] = '|'.join(fields.keys())

        measurement_tags = copy.deepcopy(tags)
        measurement_tags['type'] = metric_type

        self._points.append({
            'measurement': 'dataframes',
            'tags': measurement_tags,
            'fields': measurement_fields,
            'time': utils.ts2dt(timestamp),
        })
        if self._autocommit and len(self._points) >= self._chunk_size:
            self.commit()

    @staticmethod
    def _get_filter(key, value):
        if isinstance(value, six.text_type):
            format_string = "{}='{}'"
        elif isinstance(value, (six.integer_types, float)):
            format_string = "{}='{}'"
        return format_string.format(key, value)

    @staticmethod
    def _get_time_query(begin, end):
        return " WHERE time >= '{}' AND time < '{}'".format(
            utils.isotime(begin), utils.isotime(end))

    def _get_filter_query(self, filters):
        if not filters:
            return ''
        return ' AND ' + ' AND '.join(
            self._get_filter(k, v) for k, v in filters.items())

    @staticmethod
    def _get_type_query(types):
        if not types:
            return ''
        type_query = ' OR '.join("type='{}'".format(mtype)
                                 for mtype in types)
        return ' AND (' + type_query + ')'

    def get_total(self, types, begin, end, groupby=None, filters=None):
        query = 'SELECT SUM(qty) AS qty, SUM(price) AS price FROM "dataframes"'
        query += self._get_time_query(begin, end)
        query += self._get_filter_query(filters)
        query += self._get_type_query(types)

        if groupby:
            groupby_query = ','.join(groupby)
            query += ' GROUP BY ' + groupby_query

        query += ';'

        return self._conn.query(query)

    def retrieve(self,
                 types,
                 filters,
                 begin, end,
                 offset=0, limit=1000, paginate=True):
        query = 'SELECT * FROM "dataframes"'
        query += self._get_time_query(begin, end)
        query += self._get_filter_query(filters)
        query += self._get_type_query(types)

        if paginate:
            query += ' OFFSET {} LIMIT {}'.format(offset, limit)

        query += ';'

        total_query = 'SELECT COUNT(groupby) FROM "dataframes"'
        total_query += self._get_time_query(begin, end)
        total_query += self._get_filter_query(filters)
        total_query += self._get_type_query(types)
        total_query += ';'

        total, result = self._conn.query(total_query + query)
        total = sum(point['count'] for point in total.get_points())
        return total, result


class InfluxStorage(v2_storage.BaseStorage):

    def __init__(self, *args, **kwargs):
        super(InfluxStorage, self).__init__(*args, **kwargs)
        self._conn = InfluxClient()
        self._period = kwargs.get('period', None) or CONF.collect.period

    def init(self):
        policy = CONF.storage_influxdb.retention_policy
        database = CONF.storage_influxdb.database
        if not self._conn.retention_policy_exists(database, policy):
            LOG.error(
                'Archive policy "{}" does not exist in database "{}"'.format(
                    policy, database)
            )

    def push(self, dataframes, scope_id=None):

        for dataframe in dataframes:
            timestamp = dataframe['period']['begin']
            for metric_name, metrics in dataframe['usage'].items():
                for metric in metrics:
                    self._conn.append_point(
                        metric_name,
                        timestamp,
                        metric['vol']['qty'],
                        metric['rating']['price'],
                        metric['vol']['unit'],
                        metric['metadata'],
                        metric['groupby'],
                    )

        self._conn.commit()

    @staticmethod
    def _check_begin_end(begin, end):
        if not begin:
            begin = utils.get_month_start()
        if not end:
            end = utils.get_next_month()
        if isinstance(begin, six.text_type):
            begin = utils.iso2dt(begin)
        if isinstance(begin, int):
            begin = utils.ts2dt(begin)
        if isinstance(end, six.text_type):
            end = utils.iso2dt(end)
        if isinstance(end, int):
            end = utils.ts2dt(end)

        return begin, end

    @staticmethod
    def _build_filters(filters, group_filters):
        output = None
        if filters and group_filters:
            output = copy.deepcopy(filters)
            output.update(group_filters)
        elif group_filters:
            output = group_filters
        return output

    @staticmethod
    def _point_to_dataframe_entry(point):
        groupby = point.pop('groupby').split('|')
        metadata = point.pop('metadata').split('|')
        return {
            'vol': {
                'unit': point['unit'],
                'qty': decimal.Decimal(point['qty']),
            },
            'rating': {
                'price': point['price'],
            },
            'groupby': {key: point.get(key, '') for key in groupby},
            'metadata': {key: point.get(key, '') for key in metadata},
        }

    def _build_dataframes(self, points):
        dataframes = {}
        for point in points:
            point_type = point['type']
            if point['time'] not in dataframes.keys():
                dataframes[point['time']] = {
                    'period': {
                        'begin': point['time'],
                        'end': utils.isotime(
                            utils.iso2dt(point['time'])
                            + datetime.timedelta(seconds=self._period)),
                    },
                    'usage': {},
                }
            usage = dataframes[point['time']]['usage']
            if point_type not in usage.keys():
                usage[point_type] = []
            usage[point_type].append(self._point_to_dataframe_entry(point))

        output = list(dataframes.values())
        output.sort(key=lambda x: x['period']['begin'])
        return output

    def retrieve(self, begin=None, end=None,
                 filters=None, group_filters=None,
                 metric_types=None,
                 offset=0, limit=1000, paginate=True):
        begin, end = self._check_begin_end(begin, end)
        filters = self._build_filters(filters, group_filters)
        total, resp = self._conn.retrieve(
            metric_types, filters, begin, end, offset, limit, paginate)

        # Unfortunately, a ResultSet has no values() method, so we need to
        # get them manually
        points = []
        for _, item in resp.items():
            points += list(item)

        return {
            'total': total,
            'dataframes': self._build_dataframes(points)
        }

    @staticmethod
    def _get_total_elem(begin, end, groupby, series_groupby, point):
        output = {
            'begin': begin,
            'end': end,
            'qty': point['qty'],
            'rate': point['price'],
        }
        if groupby:
            for group in groupby:
                output[group] = series_groupby.get(group, '')
        return output

    def total(self, groupby=None,
              begin=None, end=None,
              metric_types=None,
              filters=None, group_filters=None,
              offset=0, limit=1000, paginate=True):

        begin, end = self._check_begin_end(begin, end)
        filters = self._build_filters(filters, group_filters)

        total = self._conn.get_total(
            metric_types, begin, end, groupby, filters)

        output = []
        for (series_name, series_groupby), points in total.items():
            for point in points:
                output.append(self._get_total_elem(
                    begin, end,
                    groupby,
                    series_groupby,
                    point))

        if groupby:
            output.sort(key=lambda x: [x[group] for group in groupby])
        return {
            'total': len(output),
            'results': output[offset:offset + limit] if paginate else output,
        }
