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
from oslo_config import cfg
from oslo_log import log

from cloudkitty.collector import prometheus_base
from cloudkitty.common import prometheus_client


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
    cfg.FloatOpt(
        'timeout',
        default=60,
        min=0,
        help='Timeout value for http requests',
    ),
]
cfg.CONF.register_opts(collector_prometheus_opts, PROMETHEUS_COLLECTOR_OPTS)

CONF = cfg.CONF


class PrometheusCollector(prometheus_base.PrometheusCollectorBase):
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

        self._conn = prometheus_client.PrometheusClient(
            url,
            auth=(user, password) if user and password else None,
            verify=verify,
            timeout=CONF.collector_prometheus.timeout
        )
