# -*- coding: utf-8 -*-
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
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

from cloudkitty.common import monasca_client as mon_client_utils
from cloudkitty import fetcher

MONASCA_API_VERSION = '2_0'

FETCHER_MONASCA_OPTS = 'fetcher_monasca'

fetcher_monasca_opts = [
    cfg.StrOpt('dimension_name',
               default='project_id',
               help='Monasca dimension from which scope_ids should be'
               ' collected.'),
    cfg.StrOpt('monasca_tenant_id',
               default=None,
               help='If specified, monasca client will use this ID instead of'
               ' the default one.'),
    cfg.StrOpt(
        'monasca_service_name',
        default='monasca',
        help='Name of the Monasca service (defaults to monasca)',
    ),
    cfg.StrOpt(
        'interface',
        default='internal',
        help='Endpoint URL type (defaults to internal).',
    ),
]

CONF = cfg.CONF

cfg.CONF.register_opts(fetcher_monasca_opts, FETCHER_MONASCA_OPTS)
ks_loading.register_auth_conf_options(CONF, FETCHER_MONASCA_OPTS)
ks_loading.register_session_conf_options(CONF, FETCHER_MONASCA_OPTS)


class MonascaFetcher(fetcher.BaseFetcher):
    """Monasca fetcher"""

    name = 'monasca'

    def __init__(self):
        self._conn = mon_client_utils.get_monasca_client(CONF,
                                                         FETCHER_MONASCA_OPTS)

    def get_tenants(self):
        kwargs = {
            "tenant_id": CONF.fetcher_monasca.monasca_tenant_id,
            "dimension_name": CONF.fetcher_monasca.dimension_name,
        }
        if kwargs['tenant_id'] is None:
            del kwargs['tenant_id']
        values = self._conn.metrics.list_dimension_values(**kwargs)
        return [v['dimension_value'] for v in values]
