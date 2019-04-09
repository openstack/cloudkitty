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
from voluptuous import In
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import collector
from cloudkitty.collector.exceptions import CollectError
from cloudkitty.common.prometheus_client import PrometheusClient
from cloudkitty.common.prometheus_client import PrometheusResponseError
from cloudkitty import utils as ck_utils


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
    Required('extra_args'): {
        Required('aggregation_method', default='max'):
            In([
                'avg', 'count', 'max',
                'min', 'stddev', 'stdvar',
                'sum'
            ]),
    }
}


class PrometheusCollector(collector.BaseCollector):
    collector_name = 'prometheus'

    def __init__(self, transformers, **kwargs):
        super(PrometheusCollector, self).__init__(transformers, **kwargs)
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
            metadata[meta] = data['metric'][meta]

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

        return metadata, groupby, qty

    def fetch_all(self, metric_name, start, end, scope_id, q_filter=None):
        """Returns metrics to be valorized."""
        scope_key = CONF.collect.scope_key
        method = self.conf[metric_name]['extra_args']['aggregation_method']
        groupby = self.conf[metric_name].get('groupby', [])
        metadata = self.conf[metric_name].get('metadata', [])
        period = end - start
        time = end

        query = '{0}({0}_over_time({1}{{{2}="{3}"}}[{4}s])) by ({5})'.format(
            method,
            metric_name,
            scope_key,
            scope_id,
            period,
            ', '.join(groupby + metadata),
        )

        try:
            res = self._conn.get_instant(
                query,
                time,
            )
        except PrometheusResponseError as e:
            raise CollectError(*e.args)

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

            item = self.t_cloudkitty.format_item(
                groupby,
                metadata,
                self.conf[metric_name]['unit'],
                qty=qty,
            )

            formatted_resources.append(item)

        return formatted_resources
