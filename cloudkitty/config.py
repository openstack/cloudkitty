# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
from oslo.config import cfg
from oslo.db import options as db_options  # noqa
from oslo.messaging import opts  # noqa

from cloudkitty.openstack.common import log  # noqa


auth_opts = [
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

collect_opts = [
    cfg.StrOpt('collector',
               default='ceilometer',
               help='Data collector.'),
    cfg.IntOpt('window',
               default=1800,
               help='Number of samples to collect per call.'),
    cfg.IntOpt('period',
               default=3600,
               help='Billing period in seconds.'),
    cfg.ListOpt('services',
                default=['compute'],
                help='Services to monitor.'), ]

state_opts = [
    cfg.StrOpt('backend',
               default='cloudkitty.backend.file.FileBackend',
               help='Backend for the state manager.'),
    cfg.StrOpt('basepath',
               default='/var/lib/cloudkitty/states/',
               help='Storage directory for the file state backend.'), ]

output_opts = [
    cfg.StrOpt('backend',
               default='cloudkitty.backend.file.FileBackend',
               help='Backend for the output manager.'),
    cfg.StrOpt('basepath',
               default='/var/lib/cloudkitty/states/',
               help='Storage directory for the file output backend.'),
    cfg.ListOpt('pipeline',
                default=['osrf'],
                help='Output pipeline'), ]


cfg.CONF.register_opts(auth_opts, 'auth')
cfg.CONF.register_opts(collect_opts, 'collect')
cfg.CONF.register_opts(state_opts, 'state')
cfg.CONF.register_opts(output_opts, 'output')

# oslo.db defaults
db_options.set_defaults(
    cfg.CONF,
    connection='sqlite:////var/lib/cloudkitty/cloudkitty.sqlite')
