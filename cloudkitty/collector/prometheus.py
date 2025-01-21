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
from decimal import Decimal
from decimal import localcontext
from decimal import ROUND_HALF_UP

from oslo_config import cfg
from oslo_log import log
from voluptuous import All
from voluptuous import In
from voluptuous import Optional
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import collector
from cloudkitty.collector.exceptions import CollectError
from cloudkitty.common.prometheus_client import PrometheusClient
from cloudkitty.common.prometheus_client import PrometheusResponseError
from cloudkitty import utils as ck_utils
from cloudkitty.utils import tz as tzutils


LOG = log.getLogger(__name__)

PROMETHEUS_COLLECTOR_OPTS = 'collector_prometheus'
collector_prometheus_opts = [
    cfg.StrOpt(
        'prometheus_url',
        default='',
        help='Prometheus service URL',
    ),
    cfg.StrOpt(
        'prometheus_user',
        help='Prometheus user (for basic auth only)',
    ),
    cfg.StrOpt(
        'prometheus_password',
        help='Prometheus user password (for basic auth only)',
        secret=True,
    ),
    cfg.StrOpt(
        'cafile',
        help='Custom certificate authority file path',
    ),
    cfg.BoolOpt(
        'insecure',
        default=False,
        help='Explicitly trust untrusted HTTPS responses',
    ),
]
cfg.CONF.register_opts(collector_prometheus_opts, PROMETHEUS_COLLECTOR_OPTS)

CONF = cfg.CONF

PROMETHEUS_EXTRA_SCHEMA = {
    Required('extra_args', default={}): {
        Required('aggregation_method', default='max'):
            In([
                'avg', 'count', 'max',
                'min', 'stddev', 'stdvar',
                'sum'
            ]),
        Optional('query_function'):
            In([
                'abs', 'ceil', 'exp',
                'floor', 'ln', 'log2',
                'log10', 'round', 'sqrt'
            ]),
        Optional('range_function'):
            In([
                'changes', 'delta', 'deriv',
                'idelta', 'irange', 'irate',
                'rate'
            ]),
        Optional('query_prefix', default=''): All(str),
        Optional('query_suffix', default=''): All(str),
    }
}


class PrometheusCollector(collector.BaseCollector):
    collector_name = 'prometheus'

    def __init__(self, **kwargs):
        super(PrometheusCollector, self).__init__(**kwargs)
        url = CONF.collector_prometheus.prometheus_url

        user = CONF.collector_prometheus.prometheus_user
        password = CONF.collector_prometheus.prometheus_password

        verify = True
        if CONF.collector_prometheus.cafile:
            verify = CONF.collector_prometheus.cafile
        elif CONF.collector_prometheus.insecure:
            verify = False

        self._conn = PrometheusClient(
            url,
            auth=(user, password) if user and password else None,
            verify=verify,
        )

    @staticmethod
    def check_configuration(conf):
        conf = collector.BaseCollector.check_configuration(conf)
        metric_schema = Schema(collector.METRIC_BASE_SCHEMA).extend(
            PROMETHEUS_EXTRA_SCHEMA,
        )

        output = {}
        for metric_name, metric in conf.items():
            output[metric_name] = metric_schema(metric)

        return output

    def _format_data(self, metric_name, scope_key, scope_id, start, end, data):
        """Formats Prometheus data format to Cloudkitty data format.

        Returns metadata, groupby, qty
        """
        metadata = {}
        for meta in self.conf[metric_name]['metadata']:
            metadata[meta] = data['metric'].get(meta, '')

        groupby = {scope_key: scope_id}
        for meta in self.conf[metric_name]['groupby']:
            groupby[meta] = data['metric'].get(meta, '')

        with localcontext() as ctx:
            ctx.prec = 9
            ctx.rounding = ROUND_HALF_UP

            qty = ck_utils.convert_unit(
                +Decimal(data['value'][1]),
                self.conf[metric_name]['factor'],
                self.conf[metric_name]['offset'],
            )
            mutate_map = self.conf[metric_name].get('mutate_map')
            qty = ck_utils.mutate(qty, self.conf[metric_name]['mutate'],
                                  mutate_map=mutate_map)

        return metadata, groupby, qty

    @staticmethod
    def build_query(conf, metric_name, start, end, scope_key, scope_id,
                    groupby, metadata):
        """Builds the query for the metrics to be valorized."""

        method = conf[metric_name]['extra_args']['aggregation_method']
        query_function = conf[metric_name]['extra_args'].get(
            'query_function')
        range_function = conf[metric_name]['extra_args'].get(
            'range_function')
        query_prefix = conf[metric_name]['extra_args']['query_prefix']
        query_suffix = conf[metric_name]['extra_args']['query_suffix']
        query_metric = metric_name.split('@#')[0]
        period = tzutils.diff_seconds(end, start)

        # The metric with the period
        query = '{0}{{{1}="{2}"}}[{3}s]'.format(
            query_metric,
            scope_key,
            scope_id,
            period
        )
        # Applying the aggregation_method or the range_function on
        # a Range Vector
        if range_function is not None:
            query = "{0}({1})".format(
                range_function,
                query
            )
        else:
            query = "{0}_over_time({1})".format(
                method,
                query
            )
        # Applying the query_function
        if query_function is not None:
            query = "{0}({1})".format(
                query_function,
                query
            )
        # Applying the aggregation_method on a Instant Vector
        query = "{0}({1})".format(
            method,
            query
        )
        # Filter by groupby and metadata
        query = "{0} by ({1})".format(
            query,
            ', '.join(groupby + metadata)
        )

        # Add custom query prefix
        if query_prefix:
            query = "{0} {1}".format(query_prefix, query)

        # Add custom query suffix
        if query_suffix:
            query = "{0} {1}".format(query, query_suffix)

        return query

    def fetch_all(self, metric_name, start, end, scope_id, q_filter=None):
        """Returns metrics to be valorized."""
        time = end
        metadata = self.conf[metric_name].get('metadata', [])
        groupby = self.conf[metric_name].get('groupby', [])
        scope_key = CONF.collect.scope_key

        query = self.build_query(
            self.conf,
            metric_name,
            start,
            end,
            scope_key,
            scope_id,
            groupby,
            metadata
        )

        try:
            res = self._conn.get_instant(
                query,
                time.isoformat(),
            )
        except PrometheusResponseError as e:
            raise CollectError(*e.args)

        if res['status'] == 'error':
            error_type = res['errorType']
            error_msg = res['error']
            raise CollectError("%s: %s" % (error_type, error_msg))

        # If the query returns an empty dataset,
        # return an empty list
        if not res['data']['result']:
            return []

        formatted_resources = []

        for item in res['data']['result']:
            metadata, groupby, qty = self._format_data(
                metric_name,
                scope_key,
                scope_id,
                start,
                end,
                item,
            )
            point = self._create_data_point(self.conf[metric_name], qty,
                                            0, groupby, metadata, start)
            formatted_resources.append(point)

        return formatted_resources
