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
import datetime

import influxdb
from oslo_config import cfg
from oslo_log import log
import six

from cloudkitty import dataframe
from cloudkitty.storage import v2 as v2_storage
from cloudkitty.utils import tz as tzutils


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


PERIOD_FIELD_NAME = '__ck_collect_period'


def _sanitized_groupby(groupby):
    forbidden = ('time',)
    return [g for g in groupby if g not in forbidden] if groupby else []


class InfluxClient(object):
    """Classe used to ease interaction with InfluxDB"""

    def __init__(self, chunk_size=500, autocommit=True, default_period=3600):
        """Creates an InfluxClient object.

        :param chunk_size: Size after which points should be pushed.
        :param autocommit: Set to false to disable autocommit
        :param default_period: Placeholder for the period in cae it can't
                               be determined.
        """
        self._conn = self._get_influx_client()
        self._chunk_size = chunk_size
        self._autocommit = autocommit
        self._retention_policy = CONF.storage_influxdb.retention_policy
        self._default_period = default_period
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
                     start,
                     period,
                     point):
        """Adds a point to commit to InfluxDB.

        :param metric_type: Name of the metric type
        :type metric_type: str
        :param start: Start of the period the point applies to
        :type start: datetime.datetime
        :param period: length of the period the point applies to (in seconds)
        :type period: int
        :param point: Point to push
        :type point: dataframe.DataPoint
        """
        measurement_fields = dict(point.metadata)
        measurement_fields['qty'] = float(point.qty)
        measurement_fields['price'] = float(point.price)
        measurement_fields['unit'] = point.unit
        # Unfortunately, this seems to be the fastest way: Having several
        # measurements would imply a high client-side workload, and this allows
        # us to filter out unrequired keys
        measurement_fields['groupby'] = '|'.join(point.groupby.keys())
        measurement_fields['metadata'] = '|'.join(point.metadata.keys())

        measurement_fields[PERIOD_FIELD_NAME] = period

        measurement_tags = dict(point.groupby)
        measurement_tags['type'] = metric_type

        self._points.append({
            'measurement': 'dataframes',
            'tags': measurement_tags,
            'fields': measurement_fields,
            'time': start,
        })
        if self._autocommit and len(self._points) >= self._chunk_size:
            self.commit()

    @staticmethod
    def _get_filter(key, value):
        format_string = ''
        if isinstance(value, six.string_types):
            format_string = """"{}"='{}'"""
        elif isinstance(value, (six.integer_types, float)):
            format_string = """"{}"={}"""
        return format_string.format(key, value)

    @staticmethod
    def _get_time_query(begin, end):
        return " WHERE time >= '{}' AND time < '{}'".format(
            begin.isoformat(), end.isoformat())

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
            groupby_query = ''
            if 'time' in groupby:
                groupby_query += 'time(' + str(self._default_period) + 's)'
                groupby_query += ',' if groupby else ''
            if groupby:
                groupby_query += '"' + '","'.join(
                    _sanitized_groupby(groupby)) + '"'
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
            query += ' LIMIT {} OFFSET {}'.format(limit, offset)

        query += ';'

        total_query = 'SELECT COUNT(groupby) FROM "dataframes"'
        total_query += self._get_time_query(begin, end)
        total_query += self._get_filter_query(filters)
        total_query += self._get_type_query(types)
        total_query += ';'

        total, result = self._conn.query(total_query + query)
        total = sum(point['count'] for point in total.get_points())
        return total, result

    @staticmethod
    def _get_time_query_delete(begin, end):
        output = ""
        if begin:
            output += " WHERE time >= '{}'".format(begin.isoformat())
        if end:
            output += " AND " if output else " WHERE "
            output += "time < '{}'".format(end.isoformat())
        return output

    def delete(self, begin, end, filters):
        query = 'DELETE FROM "dataframes"'
        query += self._get_time_query_delete(begin, end)
        filter_query = self._get_filter_query(filters)
        if 'WHERE' not in query and filter_query:
            query += " WHERE " + filter_query[5:]
        else:
            query += filter_query
        query += ';'
        self._conn.query(query)


class InfluxStorage(v2_storage.BaseStorage):

    def __init__(self, *args, **kwargs):
        super(InfluxStorage, self).__init__(*args, **kwargs)
        self._default_period = kwargs.get('period') or CONF.collect.period
        self._conn = InfluxClient(default_period=self._default_period)

    def init(self):
        policy = CONF.storage_influxdb.retention_policy
        database = CONF.storage_influxdb.database
        if not self._conn.retention_policy_exists(database, policy):
            LOG.error(
                'Archive policy "{}" does not exist in database "{}"'.format(
                    policy, database)
            )

    def push(self, dataframes, scope_id=None):

        for frame in dataframes:
            period = tzutils.diff_seconds(frame.end, frame.start)
            for type_, point in frame.iterpoints():
                self._conn.append_point(type_, frame.start, period, point)

        self._conn.commit()

    @staticmethod
    def _check_begin_end(begin, end):
        if not begin:
            begin = tzutils.get_month_start()
        if not end:
            end = tzutils.get_next_month()
        return tzutils.local_to_utc(begin), tzutils.local_to_utc(end)

    @staticmethod
    def _point_to_dataframe_entry(point):
        groupby = filter(bool, (point.pop('groupby', None) or '').split('|'))
        metadata = filter(bool, (point.pop('metadata', None) or '').split('|'))
        return dataframe.DataPoint(
            point['unit'],
            point['qty'],
            point['price'],
            {key: point.get(key, '') for key in groupby},
            {key: point.get(key, '') for key in metadata},
        )

    def _build_dataframes(self, points):
        dataframes = {}
        for point in points:
            point_type = point['type']
            time = tzutils.dt_from_iso(point['time'])
            period = point.get(PERIOD_FIELD_NAME) or self._default_period
            timekey = (
                time,
                tzutils.add_delta(time, datetime.timedelta(seconds=period)))
            if timekey not in dataframes.keys():
                dataframes[timekey] = dataframe.DataFrame(
                    start=timekey[0],
                    end=timekey[1])

            dataframes[timekey].add_point(
                self._point_to_dataframe_entry(point), point_type)

        output = list(dataframes.values())
        output.sort(key=lambda frame: (frame.start, frame.end))
        return output

    def retrieve(self, begin=None, end=None,
                 filters=None,
                 metric_types=None,
                 offset=0, limit=1000, paginate=True):
        begin, end = self._check_begin_end(begin, end)
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

    def delete(self, begin=None, end=None, filters=None):
        self._conn.delete(begin, end, filters)

    def _get_total_elem(self, begin, end, groupby, series_groupby, point):
        if groupby and 'time' in groupby:
            begin = tzutils.dt_from_iso(point['time'])
            period = point.get(PERIOD_FIELD_NAME) or self._default_period
            end = tzutils.add_delta(begin, datetime.timedelta(seconds=period))
        output = {
            'begin': begin,
            'end': end,
            'qty': point['qty'],
            'rate': point['price'],
        }
        if groupby:
            for group in _sanitized_groupby(groupby):
                output[group] = series_groupby.get(group, '')
        return output

    def total(self, groupby=None,
              begin=None, end=None,
              metric_types=None,
              filters=None,
              offset=0, limit=1000, paginate=True):

        begin, end = self._check_begin_end(begin, end)

        total = self._conn.get_total(
            metric_types, begin, end, groupby, filters)

        output = []
        for (series_name, series_groupby), points in total.items():
            for point in points:
                # NOTE(peschk_l): InfluxDB returns all timestamps for a given
                # period and interval, even those with no data. This filters
                # out periods with no data
                if point['qty'] is not None and point['price'] is not None:
                    output.append(self._get_total_elem(
                        tzutils.utc_to_local(begin),
                        tzutils.utc_to_local(end),
                        groupby,
                        series_groupby,
                        point))

        groupby = _sanitized_groupby(groupby)
        if groupby:
            output.sort(key=lambda x: [x[group] for group in groupby])
        return {
            'total': len(output),
            'results': output[offset:offset + limit] if paginate else output,
        }
