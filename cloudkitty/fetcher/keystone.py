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
# @author: Stéphane Albert
#
from keystoneauth1 import loading as ks_loading
from keystoneclient import client as kclient
from keystoneclient import discover
from keystoneclient import exceptions
from oslo_config import cfg

from cloudkitty import fetcher


# NOTE(mc): The deprecated section should be removed in a future release.
FETCHER_KEYSTONE_OPTS = 'fetcher_keystone'
DEPRECATED_FETCHER_KEYSTONE_OPTS = 'keystone_fetcher'

keystone_opts = ks_loading.get_auth_common_conf_options() + \
    ks_loading.get_session_conf_options()

keystone_opts = [
    cfg.Opt(
        opt.name,
        type=opt.type,
        help=opt.help,
        secret=opt.secret,
        required=opt.required,
        deprecated_group=DEPRECATED_FETCHER_KEYSTONE_OPTS,
    ) for opt in keystone_opts
]

fetcher_keystone_opts = [
    cfg.StrOpt(
        'keystone_version',
        default='2',
        help='Keystone version to use.',
        deprecated_group=DEPRECATED_FETCHER_KEYSTONE_OPTS,
    ),
]

cfg.CONF.register_opts(keystone_opts, FETCHER_KEYSTONE_OPTS)
if cfg.CONF[FETCHER_KEYSTONE_OPTS].auth_section:
    cfg.CONF.register_opts(
        keystone_opts,
        cfg.CONF[FETCHER_KEYSTONE_OPTS].auth_section,
    )

cfg.CONF.register_opts(fetcher_keystone_opts, FETCHER_KEYSTONE_OPTS)

CONF = cfg.CONF


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
        for tenant in tenant_list[:]:
            roles = getattr(self.admin_ks.roles, role_func)(
                **{'user': my_user_id,
                   tenant_attr: tenant})
            if 'rating' not in [role.name for role in roles]:
                tenant_list.remove(tenant)
        return [tenant.id for tenant in tenant_list]
