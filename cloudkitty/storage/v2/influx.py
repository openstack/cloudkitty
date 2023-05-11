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
import csv
import datetime
import influxdb
import io
import json
import re

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient
from oslo_config import cfg
from oslo_log import log
import requests

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
    cfg.IntOpt('version', help='InfluxDB version', default=1),
    cfg.IntOpt('query_timeout', help='Flux query timeout in milliseconds',
               default=3600000),
    cfg.StrOpt(
        'token',
        help='InfluxDB API token for version 2 authentication',
        default=None
    ),
    cfg.StrOpt(
        'org',
        help='InfluxDB 2 org',
        default="openstack"
    ),
    cfg.StrOpt(
        'bucket',
        help='InfluxDB 2 bucket',
        default="cloudkitty"
    ),
    cfg.StrOpt(
        'url',
        help='InfluxDB 2 URL',
        default=None
    )
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
        measurement_fields['description'] = point.description
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
        if isinstance(value, list):
            if len(value) == 1:
                return InfluxClient._get_filter(key, value[0])
            return "(" + " OR ".join('"{}"=\'{}\''.format(key, v)
                                     for v in value) + ")"

        format_string = ''
        if isinstance(value, str):
            format_string = """"{}"='{}'"""
        elif isinstance(value, (int, float)):
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
        return " AND " + InfluxClient._get_filter("type", types)

    def get_total(self, types, begin, end, custom_fields,
                  groupby=None, filters=None, limit=None):

        self.validate_custom_fields(custom_fields)

        # We validate the SQL statements. Therefore, we can ignore this
        # bandit warning here.
        query = 'SELECT %s FROM "dataframes"' % custom_fields  # nosec
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

        LOG.debug("Executing query [%s].", query)
        total = self._conn.query(query)
        LOG.debug(
            "Data [%s] received when executing query [%s].", total, query)
        return total

    @staticmethod
    def validate_custom_fields(custom_fields):
        forbidden_clauses = ["select", "from", "drop", "delete", "create",
                             "alter", "insert", "update"]
        for field in custom_fields.split(","):
            if field.lower() in forbidden_clauses:
                raise RuntimeError("Clause [%s] is not allowed in custom"
                                   " fields summary get report. The following"
                                   " clauses are not allowed [%s].",
                                   field, forbidden_clauses)

    def retrieve(self, types, filters, begin, end, offset=0, limit=1000,
                 paginate=True):
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

        LOG.debug("InfluxDB query to delete elements filtering by [%s] and "
                  "with [begin=%s, end=%s]: [%].", filters, begin, end, query)

        self._conn.query(query)

    def _get_total_elem(self, begin, end, groupby, series_groupby, point):
        if groupby and 'time' in groupby:
            begin = tzutils.dt_from_iso(point['time'])
            period = point.get(PERIOD_FIELD_NAME) or self._default_period
            end = tzutils.add_delta(begin, datetime.timedelta(seconds=period))
        output = {
            'begin': begin,
            'end': end,
        }

        for key in point.keys():
            if "time" != key:
                output[key] = point[key]

        if groupby:
            for group in _sanitized_groupby(groupby):
                output[group] = series_groupby.get(group, '')
        return output

    def process_total(self, total, begin, end, groupby, *args):
        output = []
        for (series_name, series_groupby), points in total.items():
            for point in points:
                # NOTE(peschk_l): InfluxDB returns all timestamps for a given
                # period and interval, even those with no data. This filters
                # out periods with no data

                # NOTE (rafaelweingartner): the summary get API is allowing
                # users to customize the report. Therefore, we only ignore
                # data points, if all of the entries have None values.
                # Otherwise, they are presented to the user.
                if [k for k in point.keys() if point[k]]:
                    output.append(self._get_total_elem(
                        tzutils.utc_to_local(begin),
                        tzutils.utc_to_local(end),
                        groupby,
                        series_groupby,
                        point))
        return output


class InfluxClientV2(InfluxClient):
    """Class used to facilitate interaction with InfluxDB v2

        custom_fields_rgx: Regex to parse the input custom_fields and
                           retrieve the field name, the desired alias
                           and the aggregation function to use.
                           It allows us to keep the same custom_fields
                           representation for both InfluxQL and Flux
                           queries.

    """

    custom_fields_rgx = r'([\w_\\"]+)\(([\w_\\"]+)\) (AS|as) ' \
                        r'\\?"?([\w_ \\]+)"?,? ?'

    class FluxResponseHandler(object):
        """Class used to process the response of Flux queries

            As the Flux response splits its result set by the
            requested fields, we need to merge them into a single
            one based on their groups (tags).

            Using this approach we keep the response data
            compatible with the InfluxQL result set, where we
            already have the multiple result set for each field
            merged into a single one.
        """

        def __init__(self, response, groupby, fields, begin, end,
                     field_filters):
            self.data = response
            self.field_filters = field_filters
            self.response = {}
            self.begin = begin
            self.end = end
            self.groupby = groupby
            self.fields = fields
            self.process()

        def process(self):
            """This method merges all the Flux result sets into a single one.

                To make sure the fields filtering comply with the user's
                request, we need to remove the merged entries that have None
                value for filtered fields, we need to do that because working
                with fields one by one in Flux queries is more performant
                than working with all the fields together, but it brings some
                problems when we want to filter some data. E.g:

                We want the fields A and B, grouped by C and D, and the field
                A must be 2. Imagine this query for the following
                dataset:

                    A : C : D       B : C : D
                    1 : 1 : 1       5 : 1 : 1
                    2 : 2 : 2       6 : 2 : 2
                    2 : 3 : 3       7 : 3 : 3
                    2 : 4 : 4

                The result set is going to be like:

                    A : C : D       B : C : D
                    2 : 2 : 2       5 : 1 : 1
                    2 : 3 : 3       6 : 2 : 2
                    2 : 4 : 4       7 : 3 : 3

                And the merged value is going to be like:

                    A :   B  : C : D
                 None :   5  : 1 : 1
                    2 :   6  : 2 : 2
                    2 :   7  : 3 : 3
                    2 : None : 4 : 4

                So, we need to remove the first undesired entry to get the
                correct result:

                    A :   B  : C : D
                    2 :   6  : 2 : 2
                    2 :   7  : 3 : 3
                    2 : None : 4 : 4
            """

            LOG.debug("Using fields %s to process InfluxDB V2 response.",
                      self.fields)
            LOG.debug("Start processing data [%s] of InfluxDB V2 API.",
                      self.data)
            if self.fields == ["*"] and not self.groupby:
                self.process_data_wildcard()
            else:
                self.process_data_with_fields()

            LOG.debug("Data processed by the InfluxDB V2 backend with "
                      "result [%s].", self.response)
            LOG.debug("Start sanitizing the response of Influx V2 API.")
            self.sanitize_filtered_entries()
            LOG.debug("Response sanitized [%s] for InfluxDB V2 API.",
                      self.response)

        def process_data_wildcard(self):
            LOG.debug("Processing wildcard response for InfluxDB V2 API.")
            found_fields = set()
            for r in self.data:
                if self.is_header_entry(r):
                    LOG.debug("Skipping header entry: [%s].", r)
                    continue
                r_key = ''.join(sorted(r.values()))
                found_fields.add(r['_field'])
                r_value = r
                r_value['begin'] = self.begin
                r_value['end'] = self.end
                self.response.setdefault(
                    r_key, r_value)[r['result']] = float(r['_value'])

        def process_data_with_fields(self):
            for r in self.data:
                if self.is_header_entry(r):
                    LOG.debug("Skipping header entry: [%s].", r)
                    continue
                r_key = ''
                r_value = {f: None for f in self.fields}
                r_value['begin'] = self.begin
                r_value['end'] = self.end
                for g in (self.groupby or []):
                    val = r.get(g)
                    r_key += val or ''
                    r_value[g] = val

                self.response.setdefault(
                    r_key, r_value)[r['result']] = float(r['_value'])

        @staticmethod
        def is_header_entry(entry):
            """Check header entries.

                As the response contains multiple resultsets,
                each entry in the response CSV has its own
                header, which is the same for all the result sets,
                but the CSV parser does not ignore it
                and processes all headers except the first as a
                dict entry, so for these cases, each dict's value
                is going to be the same as the dict's key, so we
                are picking one and if it is this case, we skip it.

            """

            return entry.get('_start') == '_start'

        def sanitize_filtered_entries(self):
            """Removes entries where filtered fields have None as value."""

            for d in self.field_filters or []:
                for k in list(self.response.keys()):
                    if self.response[k][d] is None:
                        self.response.pop(k, None)

    def __init__(self, default_period=None):
        super().__init__(default_period=default_period)
        self.client = InfluxDBClient(
                url=CONF.storage_influxdb.url,
                timeout=CONF.storage_influxdb.query_timeout,
                token=CONF.storage_influxdb.token,
                org=CONF.storage_influxdb.org)
        self._conn = self.client

    def retrieve(self, types, filters, begin, end, offset=0, limit=1000,
                 paginate=True):

        query = self.get_query(begin, end, '*', filters=filters)
        response = self.query(query)
        output = self.process_total(
            response, begin, end, None, '*', filters)
        LOG.debug("Retrieved output %s", output)
        results = {'results': output[
                              offset:offset + limit] if paginate else output}
        return len(output), results

    def delete(self, begin, end, filters):
        predicate = '_measurement="dataframes"'
        f = self.get_group_filters_query(
            filters, fmt=lambda x: '"' + str(x) + '"')
        if f:
            f = f.replace('==', '=').replace('and', 'AND')
            predicate += f'{f}'

        LOG.debug("InfluxDB v2 deleting elements filtering by [%s] and "
                  "with [begin=%s, end=%s].", predicate, begin, end)
        delete_api = self.client.delete_api()
        delete_api.delete(begin, end, bucket=CONF.storage_influxdb.bucket,
                          predicate=predicate)

    def process_total(self, total, begin, end, groupby, custom_fields,
                      filters):
        cf = self.get_custom_fields(custom_fields)
        fields = list(map(lambda f: f[2], cf))
        c_fields = {f[1]: f[2] for f in cf}
        field_filters = [c_fields[f] for f in filters if f in c_fields]
        handler = self.FluxResponseHandler(total, groupby, fields, begin, end,
                                           field_filters)
        return list(handler.response.values())

    def commit(self):
        total_points = len(self._points)
        if len(self._points) < 1:
            return
        LOG.debug('Pushing {} points to InfluxDB'.format(total_points))
        self.write_points(self._points,
                          retention_policy=self._retention_policy)
        self._points = []

    def write_points(self, points, retention_policy=None):
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        [write_api.write(
            bucket=CONF.storage_influxdb.bucket, record=p)
            for p in points]

    def _get_filter_query(self, filters):
        if not filters:
            return ''
        return ' and ' + ' and '.join(
            self._get_filter(k, v) for k, v in filters.items())

    def get_custom_fields(self, custom_fields):

        if not custom_fields:
            return []

        if custom_fields.strip() == '*':
            return [('*', '*', '*')]

        groups = [list(i.groups()) for i in re.finditer(
            self.custom_fields_rgx, custom_fields)]

        # Remove the "As|as" group that is useless.
        if groups:
            for g in groups:
                del g[2]

        return groups

    def get_group_filters_query(self, group_filters, fmt=lambda x: f'r.{x}'):
        if not group_filters:
            return ''

        get_val = (lambda x: x if isinstance(v, (int, float)) or
                   x.isnumeric() else f'"{x}"')

        f = ''
        for k, v in group_filters.items():
            if isinstance(v, (list, tuple)):
                if len(v) == 1:
                    f += f' and {fmt(k)}=={get_val(v[0])}'
                    continue

                f += ' and (%s)' % ' or '.join([f'{fmt(k)}=={get_val(val)}'
                                                for val in v])
                continue

            f += f' and {fmt(k)}=={get_val(v)}'

        return f

    def get_field_filters_query(self, field_filters,
                                fmt=lambda x: 'r["_value"]'):
        return self.get_group_filters_query(field_filters, fmt)

    def get_custom_fields_query(self, custom_fields, query, field_filters,
                                group_filters, limit=None, groupby=None):
        if not groupby:
            groupby = []
        if not custom_fields:
            custom_fields = 'sum(price) AS price,sum(qty) AS qty'
        columns_to_keep = ', '.join(map(lambda g: f'"{g}"', groupby))
        columns_to_keep += ', "_field", "_value", "_start", "_stop"'
        new_query = ''
        LOG.debug("Custom fields: %s", custom_fields)
        LOG.debug("Custom fields processed: %s",
                  self.get_custom_fields(custom_fields))
        for operation, field, alias in self.get_custom_fields(custom_fields):
            LOG.debug("Generating query with operation [%s],"
                      " field [%s] and alias [%s]", operation, field, alias)
            field_filter = {}
            if field_filters and field in field_filters:
                field_filter = {field: field_filters[field]}

            if field == '*':
                group_filter = self.get_group_filters_query(
                    group_filters).replace(" and ", "", 1)
                filter_to_replace = f'|> filter(fn: (r) => {group_filter})'
                new_query += query.replace(
                    '<placeholder-filter>',
                    filter_to_replace).replace(
                    '<placeholder-operations>',
                    f'''|> drop(columns: ["_time"])
                      {'|> limit(n: ' + str(limit) + ')' if limit else ''}
                        |> yield(name: "result")''')
                continue

            new_query += query.replace(
                '<placeholder-filter>',
                f'|> filter(fn: (r) => r["_field"] == '
                f'"{field}" {self.get_group_filters_query(group_filters)} '
                f'{self.get_field_filters_query(field_filter)})'
            ).replace(
                '<placeholder-operations>',
                f'''|> {operation.lower()}()
            |> keep(columns: [{columns_to_keep}])
            |> set(key: "_field", value: "{alias}")
            |> yield(name: "{alias}")''')
        return new_query

    def get_groupby(self, groupby):
        if not groupby:
            return "|> group()"
        return f'''|> group(columns: [{','.join([f'"{g}"'
                                                 for g in groupby])}])'''

    def get_time_range(self, begin, end):
        if not begin or not end:
            return ''
        return f'|> range(start: {begin.isoformat()}, stop: {end.isoformat()})'

    def get_query(self, begin, end, custom_fields, groupby=None, filters=None,
                  limit=None):

        custom_fields_processed = list(
            map(lambda x: x[1], self.get_custom_fields(custom_fields)))
        field_filters = dict(filter(
            lambda f: f[0] in custom_fields_processed, filters.items()))
        group_filters = dict(filter(
            lambda f: f[0] not in field_filters, filters.items()))

        query = f'''
        from(bucket:"{CONF.storage_influxdb.bucket}")
            {self.get_time_range(begin, end)}
            |> filter(fn: (r) => r["_measurement"] == "dataframes")
            <placeholder-filter>
            {self.get_groupby(groupby)}
            <placeholder-operations>
        '''

        LOG.debug("Field Filters: %s", field_filters)
        LOG.debug("Group Filters: %s", group_filters)
        query = self.get_custom_fields_query(custom_fields, query,
                                             field_filters, group_filters,
                                             limit, groupby)
        return query

    def query(self, query):
        url_base = CONF.storage_influxdb.url
        org = CONF.storage_influxdb.org
        url = f'{url_base}/api/v2/query?org={org}'
        response = requests.post(
            url=url,
            headers={
                'Content-type': 'application/json',
                'Authorization': f'Token {CONF.storage_influxdb.token}'},
            data=json.dumps({
                'query': query}))
        response_text = response.text
        LOG.debug("Raw Response: [%s].", response_text)
        handled_response = []
        for csv_tables in response_text.split(',result,table,'):
            csv_tables = ',result,table,' + csv_tables
            LOG.debug("Processing CSV [%s].", csv_tables)
            processed = list(csv.DictReader(io.StringIO(csv_tables)))
            LOG.debug("Processed CSV in dict [%s]", processed)
            handled_response.extend(processed)
        return handled_response

    def get_total(self, types, begin, end, custom_fields,
                  groupby=None, filters=None, limit=None):

        LOG.debug("Query types: %s", types)
        if types:
            if not filters:
                filters = {}
            filters['type'] = types

        LOG.debug("Query filters: %s", filters)
        query = self.get_query(begin, end, custom_fields,
                               groupby, filters, limit)

        LOG.debug("Executing the Flux query [%s].", query)

        return self.query(query)


class InfluxStorage(v2_storage.BaseStorage):

    def __init__(self, *args, **kwargs):
        super(InfluxStorage, self).__init__(*args, **kwargs)
        self._default_period = kwargs.get('period') or CONF.collect.period
        if CONF.storage_influxdb.version == 2:
            self._conn = InfluxClientV2(default_period=self._default_period)
        else:
            self._conn = InfluxClient(default_period=self._default_period)

    def init(self):
        if CONF.storage_influxdb.version == 2:
            return
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

    def total(self, groupby=None, begin=None, end=None, metric_types=None,
              filters=None, offset=0, limit=1000, paginate=True,
              custom_fields="SUM(qty) AS qty, SUM(price) AS rate"):

        begin, end = self._check_begin_end(begin, end)
        groupby = self.parse_groupby_syntax_to_groupby_elements(groupby)

        total = self._conn.get_total(metric_types, begin, end,
                                     custom_fields, groupby, filters, limit)

        output = self._conn.process_total(
            total, begin, end, groupby, custom_fields, filters)

        groupby = _sanitized_groupby(groupby)
        if groupby:
            output.sort(key=lambda x: [x[group] or "" for group in groupby])

        return {
            'total': len(output),
            'results': output[offset:offset + limit] if paginate else output,
        }
