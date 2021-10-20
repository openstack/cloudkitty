# -*- coding: utf-8 -*-
# !/usr/bin/env python
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
from keystoneauth1 import loading as ks_loading
from keystoneclient import client as kclient
from keystoneclient import discover
from keystoneclient import exceptions
from oslo_config import cfg
from oslo_log import log as logging

from cloudkitty import fetcher

FETCHER_KEYSTONE_OPTS = 'fetcher_keystone'

fetcher_keystone_opts = [
    cfg.StrOpt(
        'keystone_version',
        default='3',
        help='Keystone version to use.',
    ),
    cfg.BoolOpt(
        'ignore_rating_role',
        default=False,
        help='Skip rating role check for cloudkitty user',
    ),
    cfg.BoolOpt(
        'ignore_disabled_tenants',
        default=False,
        help='Stop rating disabled tenants',
    ),
]

ks_loading.register_session_conf_options(cfg.CONF, FETCHER_KEYSTONE_OPTS)
ks_loading.register_auth_conf_options(cfg.CONF, FETCHER_KEYSTONE_OPTS)
cfg.CONF.register_opts(fetcher_keystone_opts, FETCHER_KEYSTONE_OPTS)

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class KeystoneFetcher(fetcher.BaseFetcher):
    """Keystone tenants fetcher."""

    name = 'keystone'

    def __init__(self):
        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            FETCHER_KEYSTONE_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            FETCHER_KEYSTONE_OPTS,
            auth=self.auth)
        self.admin_ks = kclient.Client(
            version=CONF.fetcher_keystone.keystone_version,
            session=self.session,
            auth_url=self.auth.auth_url)

    def get_tenants(self):
        keystone_version = discover.normalize_version_number(
            CONF.fetcher_keystone.keystone_version)
        auth_dispatch = {(3,): ('project', 'projects', 'list'),
                         (2,): ('tenant', 'tenants', 'roles_for_user')}
        for auth_version, auth_version_mapping in auth_dispatch.items():
            if discover.version_match(auth_version, keystone_version):
                return self._do_get_tenants(auth_version_mapping)
        msg = "Keystone version you've specified is not supported"
        raise exceptions.VersionNotAvailable(msg)

    def _do_get_tenants(self, auth_version_mapping):
        tenant_attr, tenants_attr, role_func = auth_version_mapping
        tenant_list = getattr(self.admin_ks, tenants_attr).list()
        my_user_id = self.session.get_user_id()
        ignore_rating_role = CONF.fetcher_keystone.ignore_rating_role
        ignore_disabled_tenants = CONF.fetcher_keystone.ignore_disabled_tenants
        LOG.debug('Total number of tenants : %s', len(tenant_list))
        for tenant in tenant_list[:]:
            if ignore_disabled_tenants:
                if not tenant.enabled:
                    tenant_list.remove(tenant)
                    LOG.debug('Disabled tenant name %s with id %s skipped.',
                              tenant.name, tenant.id)
                    continue
            if not ignore_rating_role:
                roles = getattr(self.admin_ks.roles, role_func)(
                    **{'user': my_user_id,
                       tenant_attr: tenant})
                if 'rating' not in [role.name for role in roles]:
                    tenant_list.remove(tenant)
        LOG.debug('Number of tenants to rate : %s', len(tenant_list))
        return [tenant.id for tenant in tenant_list]
