# -*- coding: utf-8 -*-
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
# @author: Martin CAMEY
#
from decimal import Decimal
from decimal import localcontext
from decimal import ROUND_HALF_UP

from oslo_config import cfg
from oslo_log import log
import requests
from voluptuous import All
from voluptuous import Length
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import collector
from cloudkitty import utils as ck_utils


LOG = log.getLogger(__name__)

PROMETHEUS_COLLECTOR_OPTS = 'prometheus_collector'
pcollector_collector_opts = [
    cfg.StrOpt(
        'prometheus_url',
        default='',
        help='Prometheus service URL',
    ),
]
cfg.CONF.register_opts(pcollector_collector_opts, PROMETHEUS_COLLECTOR_OPTS)

CONF = cfg.CONF

PROMETHEUS_EXTRA_SCHEMA = {
    Required('extra_args'): {
        Required('query'): All(str, Length(min=1)),
    }
}


class PrometheusClient(object):
    @classmethod
    def build_query(cls, source, query, start, end, period, metric_name):
        """Build PromQL instant queries."""
        start = ck_utils.iso8601_from_timestamp(start)
        end = ck_utils.iso8601_from_timestamp(end)

        if '$period' in query:
            try:
                query = ck_utils.template_str_substitute(
                    query, {'period': str(period) + 's'},
                )
            except (KeyError, ValueError):
                raise collector.NoDataCollected(
                    collector.collector_name,
                    metric_name
                )

        # Due to the design of Cloudkitty, only instant queries are supported.
        # In that case 'time' equals 'end' and
        # the window time is reprezented by the period.
        return source + '/query?query=' + query + '&time=' + end

    @classmethod
    def get_data(cls, source, query, start, end, period, metric_name):
        url = cls.build_query(
            source,
            query,
            start,
            end,
            period,
            metric_name,
        )

        return requests.get(url).json()


class PrometheusCollector(collector.BaseCollector):
    collector_name = 'prometheus'

    def __init__(self, transformers, **kwargs):
        super(PrometheusCollector, self).__init__(transformers, **kwargs)

    @staticmethod
    def check_configuration(conf):
        """Check metrics configuration."""
        conf = Schema(collector.CONF_BASE_SCHEMA)(conf)
        metric_schema = Schema(collector.METRIC_BASE_SCHEMA).extend(
            PROMETHEUS_EXTRA_SCHEMA,
        )

        output = {}
        for metric_name, metric in conf['metrics'].items():
            output[metric_name] = metric_schema(metric)
        return output

    def _format_data(self, metric_name, project_id, start, end, data):
        """Formats Prometheus data format to Cloudkitty data format.

        Returns metadata, groupby, qty
        """
        metadata = {}
        for meta in self.conf[metric_name]['metadata']:
            metadata[meta] = data['metric'][meta]

        groupby = {}
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

    def fetch_all(self, metric_name, start, end, project_id, q_filter=None):
        """Returns metrics to be valorized."""
        # NOTE(mc): Remove potential trailing '/' to avoid
        # url building problems
        url = CONF.prometheus_collector.prometheus_url
        if url.endswith('/'):
            url = url[:-1]

        res = PrometheusClient.get_data(
            url,
            self.conf[metric_name]['extra_args']['query'],
            start,
            end,
            self.period,
            metric_name,
        )

        # If the query returns an empty dataset,
        # raise a NoDataCollected exception.
        if not res['data']['result']:
            raise collector.NoDataCollected(self.collector_name, metric_name)

        formatted_resources = []

        for item in res['data']['result']:
            metadata, groupby, qty = self._format_data(
                metric_name,
                project_id,
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
