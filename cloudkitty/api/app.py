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
import os

from oslo_config import cfg
from oslo_log import log
from paste import deploy
import pecan

from cloudkitty.api import config as api_config
from cloudkitty.api import hooks
from cloudkitty import service
from cloudkitty import storage


LOG = log.getLogger(__name__)

auth_opts = [
    cfg.StrOpt('api_paste_config',
               default="api_paste.ini",
               help="Configuration file for WSGI definition of API."),
    cfg.StrOpt('auth_strategy',
               choices=['noauth', 'keystone'],
               default='keystone',
               help=("The strategy to use for auth. Supports noauth and "
                     "keystone")),
]

api_opts = [
    cfg.IPOpt('host_ip',
              default='0.0.0.0',
              help='The listen IP for the cloudkitty API server.'),
    cfg.PortOpt('port',
                default=8889,
                help='The port for the cloudkitty API server.'),
    cfg.BoolOpt('pecan_debug',
                default=False,
                help='Toggle Pecan Debug Middleware.'),
]

CONF = cfg.CONF
CONF.register_opts(auth_opts)
CONF.register_opts(api_opts, group='api')


def get_pecan_config():
    # Set up the pecan configuration
    filename = api_config.__file__.replace('.pyc', '.py')
    return pecan.configuration.conf_from_file(filename)


def setup_app(pecan_config=None, extra_hooks=None):

    app_conf = get_pecan_config()
    storage_backend = storage.get_storage()

    app_hooks = [
        hooks.RPCHook(),
        hooks.StorageHook(storage_backend),
        hooks.ContextHook(),
    ]

    app = pecan.make_app(
        app_conf.app.root,
        static_root=app_conf.app.static_root,
        template_path=app_conf.app.template_path,
        debug=CONF.api.pecan_debug,
        force_canonical=getattr(app_conf.app, 'force_canonical', True),
        hooks=app_hooks,
        guess_content_type_from_ext=False
    )

    return app


def load_app():
    cfg_file = None
    cfg_path = cfg.CONF.api_paste_config
    if not os.path.isabs(cfg_path):
        cfg_file = CONF.find_file(cfg_path)
    elif os.path.exists(cfg_path):
        cfg_file = cfg_path

    if not cfg_file:
        raise cfg.ConfigFilesNotFoundError([cfg.CONF.api_paste_config])
    LOG.info("Full WSGI config used: %s", cfg_file)
    appname = "cloudkitty+{}".format(cfg.CONF.auth_strategy)
    LOG.info("Cloudkitty api with '%s' auth type will be loaded.",
             cfg.CONF.auth_strategy)
    return deploy.loadapp("config:" + cfg_file, name=appname)


def build_wsgi_app(argv=None):
    service.prepare_service()
    return load_app()


def app_factory(global_config, **local_conf):
    return setup_app()
