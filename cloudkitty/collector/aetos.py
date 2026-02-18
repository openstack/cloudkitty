# Copyright 2026 Red Hat, Inc.
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
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log

from cloudkitty.collector import prometheus_base
from cloudkitty.common import aetos_client


LOG = log.getLogger(__name__)

COLLECTOR_AETOS_OPTS = 'collector_aetos'

collector_aetos_opts = [
    cfg.StrOpt(
        'interface',
        default='public',
        choices=['internal', 'public', 'admin'],
        help='Type of endpoint to use in keystoneclient.',
    ),
    cfg.StrOpt(
        'region_name',
        default=None,
        help='Region in Identity service catalog to use for communication '
             'with the OpenStack service.',
    ),
]

ks_loading.register_session_conf_options(cfg.CONF, COLLECTOR_AETOS_OPTS)
ks_loading.register_auth_conf_options(cfg.CONF, COLLECTOR_AETOS_OPTS)
cfg.CONF.register_opts(collector_aetos_opts, COLLECTOR_AETOS_OPTS)

CONF = cfg.CONF


class AetosCollector(prometheus_base.PrometheusCollectorBase):
    """Collector for Aetos (Prometheus with Keystone authentication).

    Aetos is a reverse-proxy that adds Keystone authentication to Prometheus.
    This collector uses the same query logic as PrometheusCollector but
    authenticates via Keystone.
    """

    collector_name = 'aetos'

    def __init__(self, **kwargs):
        """Initialize Aetos collector with Keystone authentication."""
        super(AetosCollector, self).__init__(**kwargs)

        auth_plugin = ks_loading.load_auth_from_conf_options(
            CONF,
            COLLECTOR_AETOS_OPTS,
        )

        session = ks_loading.load_session_from_conf_options(
            CONF, COLLECTOR_AETOS_OPTS, auth=auth_plugin)

        adapter_options = {
            'interface': CONF.collector_aetos.interface,
            'region_name': CONF.collector_aetos.region_name,
            'service_type': 'metric-storage',
        }

        self._conn = aetos_client.AetosClient(session, adapter_options)

        LOG.debug(
            "Initialized Aetos collector with interface=%s, region=%s",
            adapter_options['interface'],
            adapter_options['region_name']
        )
