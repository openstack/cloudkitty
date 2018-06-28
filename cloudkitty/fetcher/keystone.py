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


KEYSTONE_FETCHER_OPTS = 'keystone_fetcher'
keystone_common_opts = ks_loading.get_auth_common_conf_options()
keystone_fetcher_opts = [
    cfg.StrOpt('keystone_version',
               default='2',
               help='Keystone version to use.'), ]

cfg.CONF.register_opts(keystone_common_opts, KEYSTONE_FETCHER_OPTS)
cfg.CONF.register_opts(keystone_fetcher_opts, KEYSTONE_FETCHER_OPTS)
ks_loading.register_session_conf_options(
    cfg.CONF,
    KEYSTONE_FETCHER_OPTS)
ks_loading.register_auth_conf_options(
    cfg.CONF,
    KEYSTONE_FETCHER_OPTS)
CONF = cfg.CONF


class KeystoneFetcher(fetcher.BaseFetcher):
    """Keystone tenants fetcher."""

    name = 'keystone'

    def __init__(self):
        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            KEYSTONE_FETCHER_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            KEYSTONE_FETCHER_OPTS,
            auth=self.auth)
        self.admin_ks = kclient.Client(
            version=CONF.keystone_fetcher.keystone_version,
            session=self.session,
            auth_url=self.auth.auth_url)

    def get_tenants(self):
        keystone_version = discover.normalize_version_number(
            CONF.keystone_fetcher.keystone_version)
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
