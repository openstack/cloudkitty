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
from keystoneclient import auth as ks_auth
from keystoneclient import client as kclient
from keystoneclient import session as ks_session
from oslo_config import cfg

from cloudkitty import tenant_fetcher

KEYSTONE_FETCHER_OPTS = 'keystone_fetcher'
keystone_fetcher_opts = [
    cfg.StrOpt('keystone_version',
               default='2',
               help='Keystone version to use.'), ]

cfg.CONF.register_opts(keystone_fetcher_opts, KEYSTONE_FETCHER_OPTS)
ks_session.Session.register_conf_options(
    cfg.CONF,
    KEYSTONE_FETCHER_OPTS)
ks_auth.register_conf_options(
    cfg.CONF,
    KEYSTONE_FETCHER_OPTS)
CONF = cfg.CONF


class KeystoneFetcher(tenant_fetcher.BaseFetcher):
    """Keystone tenants fetcher."""

    def __init__(self):
        self.auth = ks_auth.load_from_conf_options(
            CONF,
            KEYSTONE_FETCHER_OPTS)
        self.session = ks_session.Session.load_from_conf_options(
            CONF,
            KEYSTONE_FETCHER_OPTS,
            auth=self.auth)
        self.admin_ks = kclient.Client(
            version=CONF.keystone_fetcher.keystone_version,
            session=self.session,
            auth_url=self.auth.auth_url)

    def get_tenants(self):
        tenant_list = self.admin_ks.tenants.list()
        my_user_id = self.session.get_user_id()
        for tenant in tenant_list:
            roles = self.admin_ks.roles.roles_for_user(
                my_user_id,
                tenant)
            if 'rating' not in [role.name for role in roles]:
                tenant_list.remove(tenant)
        return [tenant.id for tenant in tenant_list]
