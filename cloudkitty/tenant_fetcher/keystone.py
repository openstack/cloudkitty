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
from keystoneclient.v2_0 import client as kclient
from oslo.config import cfg

from cloudkitty import tenant_fetcher

keystone_fetcher_opts = [
    cfg.StrOpt('username',
               default='',
               help='OpenStack username.'),
    cfg.StrOpt('password',
               default='',
               help='OpenStack password.'),
    cfg.StrOpt('tenant',
               default='',
               help='OpenStack tenant.'),
    cfg.StrOpt('region',
               default='',
               help='OpenStack region.'),
    cfg.StrOpt('url',
               default='',
               help='OpenStack auth URL.'), ]

cfg.CONF.register_opts(keystone_fetcher_opts, 'keystone_fetcher')
CONF = cfg.CONF


class KeystoneFetcher(tenant_fetcher.BaseFetcher):
    """Keystone tenants fetcher."""

    def __init__(self):
        self.user = CONF.keystone_fetcher.username
        self.password = CONF.keystone_fetcher.password
        self.tenant = CONF.keystone_fetcher.tenant
        self.region = CONF.keystone_fetcher.region
        self.keystone_url = CONF.keystone_fetcher.url
        self.admin_ks = kclient.Client(
            username=self.user,
            password=self.password,
            tenant_name=self.tenant,
            region_name=self.region,
            auth_url=self.keystone_url)

    def get_tenants(self):
        ks = kclient.Client(username=self.user,
                            password=self.password,
                            auth_url=self.keystone_url,
                            region_name=self.region)
        tenant_list = ks.tenants.list()
        for tenant in tenant_list:
            roles = self.admin_ks.roles.roles_for_user(self.admin_ks.user_id,
                                                       tenant)
            if 'rating' not in [role.name for role in roles]:
                tenant_list.remove(tenant)
        return [tenant.id for tenant in tenant_list]
