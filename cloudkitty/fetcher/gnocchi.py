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
import requests

from gnocchiclient import auth as gauth
from gnocchiclient import client as gclient
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log

from cloudkitty.common import custom_session
from cloudkitty import fetcher


LOG = log.getLogger(__name__)

FETCHER_GNOCCHI_OPTS = 'fetcher_gnocchi'

fetcher_gnocchi_opts = ks_loading.get_auth_common_conf_options()
gfetcher_opts = [
    cfg.StrOpt('scope_attribute',
               default='project_id',
               help='Attribute from which scope_ids should be collected.'),
    cfg.ListOpt('resource_types',
                default=['generic'],
                help='List of gnocchi resource types. All if left blank'),
    cfg.StrOpt(
        'gnocchi_auth_type',
        default='keystone',
        choices=['keystone', 'basic'],
        help='Gnocchi auth type (keystone or basic). Keystone credentials '
        'can be specified through the "auth_section" parameter',
    ),
    cfg.StrOpt(
        'gnocchi_user',
        default='',
        help='Gnocchi user (for basic auth only)',
    ),
    cfg.StrOpt(
        'gnocchi_endpoint',
        default='',
        help='Gnocchi endpoint (for basic auth only)',
    ),
    cfg.StrOpt(
        'interface',
        default='internalURL',
        help='Endpoint URL type (for keystone auth only)',
    ),
    cfg.StrOpt(
        'region_name',
        default='RegionOne',
        help='Region Name',
    ),
    cfg.IntOpt(
        'http_pool_maxsize',
        default=requests.adapters.DEFAULT_POOLSIZE,
        help='If the value is not defined, we use the value defined by '
             'requests.adapters.DEFAULT_POOLSIZE',
    )
]


cfg.CONF.register_opts(fetcher_gnocchi_opts, FETCHER_GNOCCHI_OPTS)
cfg.CONF.register_opts(gfetcher_opts, FETCHER_GNOCCHI_OPTS)
ks_loading.register_session_conf_options(
    cfg.CONF,
    FETCHER_GNOCCHI_OPTS)
ks_loading.register_auth_conf_options(
    cfg.CONF,
    FETCHER_GNOCCHI_OPTS)
CONF = cfg.CONF


class GnocchiFetcher(fetcher.BaseFetcher):
    """Gnocchi scope_id fetcher."""

    name = 'gnocchi'

    def __init__(self):
        super(GnocchiFetcher, self).__init__()

        adapter_options = {'connect_retries': 3}
        if CONF.fetcher_gnocchi.gnocchi_auth_type == 'keystone':
            auth_plugin = ks_loading.load_auth_from_conf_options(
                CONF,
                FETCHER_GNOCCHI_OPTS,
            )
            adapter_options['interface'] = CONF.fetcher_gnocchi.interface
        else:
            auth_plugin = gauth.GnocchiBasicPlugin(
                user=CONF.fetcher_gnocchi.gnocchi_user,
                endpoint=CONF.fetcher_gnocchi.gnocchi_endpoint,
            )
        adapter_options['region_name'] = CONF.fetcher_gnocchi.region_name

        verify = True
        if CONF.fetcher_gnocchi.cafile:
            verify = CONF.fetcher_gnocchi.cafile
        elif CONF.fetcher_gnocchi.insecure:
            verify = False

        self._conn = gclient.Client(
            '1',
            session=custom_session.create_custom_session(
                {'auth': auth_plugin, 'verify': verify},
                CONF.fetcher_gnocchi.http_pool_maxsize),
            adapter_options=adapter_options,
        )

    def get_tenants(self):
        resources = []
        resource_types = CONF.fetcher_gnocchi.resource_types
        for resource_type in resource_types:
            marker = None
            while True:
                resources_chunk = self._conn.resource.list(
                    resource_type=resource_type,
                    marker=marker,
                    details=True)
                if len(resources_chunk) < 1 or (
                        len(resources) == 1 and resources[0]['id'] == marker):
                    break
                resources += resources_chunk
                marker = resources_chunk[-1]['id']

        scope_attribute = CONF.fetcher_gnocchi.scope_attribute
        scope_ids = [
            resource.get(scope_attribute, None) for resource in resources]
        scope_ids = [s_id for s_id in scope_ids if s_id]
        # Returning unique ids
        return list(set(scope_ids))
