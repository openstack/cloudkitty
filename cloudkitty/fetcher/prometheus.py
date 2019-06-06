# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
from oslo_config import cfg

from cloudkitty.common.prometheus_client import PrometheusClient
from cloudkitty.common.prometheus_client import PrometheusResponseError
from cloudkitty import fetcher


class PrometheusFetcherError(Exception):
    pass


FETCHER_PROMETHEUS_OPTS = 'fetcher_prometheus'

fetcher_prometheus_opts = [
    cfg.StrOpt(
        'metric',
        help='Metric from which scope_ids should be requested',
    ),
    cfg.StrOpt(
        'scope_attribute',
        default='project_id',
        help='Attribute from which scope_ids should be collected',
    ),
    cfg.StrOpt(
        'prometheus_url',
        help='Prometheus service URL',
    ),
    cfg.StrOpt(
        'prometheus_user',
        default='',
        help='Prometheus user (for basic auth only)',
    ),
    cfg.StrOpt(
        'prometheus_password',
        default='',
        help='Prometheus user (for basic auth only)',
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
    cfg.DictOpt(
        'filters',
        default=dict(),
        help='Metadata to filter out the scope_ids discovery request response',
    ),
]

cfg.CONF.register_opts(fetcher_prometheus_opts, FETCHER_PROMETHEUS_OPTS)

CONF = cfg.CONF


class PrometheusFetcher(fetcher.BaseFetcher):
    """Prometheus scope_id fetcher"""

    name = 'prometheus'

    def __init__(self):
        super(PrometheusFetcher, self).__init__()
        url = CONF.fetcher_prometheus.prometheus_url

        user = CONF.fetcher_prometheus.prometheus_user
        password = CONF.fetcher_prometheus.prometheus_password

        verify = True
        if CONF.fetcher_prometheus.cafile:
            verify = CONF.fetcher_prometheus.cafile
        elif CONF.fetcher_prometheus.insecure:
            verify = False

        self._conn = PrometheusClient(
            url,
            auth=(user, password) if user and password else None,
            verify=verify,
        )

    def get_tenants(self):
        metric = CONF.fetcher_prometheus.metric
        scope_attribute = CONF.fetcher_prometheus.scope_attribute
        filters = CONF.fetcher_prometheus.filters

        metadata = ''
        # Preformatting filters as {label1="value1", label2="value2"}
        if filters:
            metadata = '{{{}}}'.format(', '.join([
                '{}="{}"'.format(k, v) for k, v in filters.items()
            ]))

        # Formatting PromQL query
        query = 'max({}{}) by ({})'.format(
            metric,
            metadata,
            scope_attribute,
        )

        try:
            res = self._conn.get_instant(query)
        except PrometheusResponseError as e:
            raise PrometheusFetcherError(*e.args)

        try:
            result = res['data']['result']
            if not result:
                return []

            scope_ids = [
                item['metric'][scope_attribute] for item in result
                if scope_attribute in item['metric'].keys()
            ]
        except KeyError:
            msg = (
                'Unexpected Prometheus server response '
                '"{}" for "{}"'
            ).format(
                res,
                query,
            )
            raise PrometheusFetcherError(msg)

        # Returning unique ids
        return list(set(scope_ids))
