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
import os

import flask
import flask_restful
from oslo_config import cfg
from oslo_log import log
from paste import deploy

from werkzeug.middleware import dispatcher

from cloudkitty.api import root as api_root
from cloudkitty.api.v1 import get_api_app as get_v1_app
from cloudkitty.api.v2 import get_api_app as get_v2_app
from cloudkitty import service


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
    cfg.PortOpt('port',
                default=8889,
                help='The port for the cloudkitty API server.'),
]

CONF = cfg.CONF
CONF.import_opt('version', 'cloudkitty.storage', 'storage')

CONF.register_opts(auth_opts)
CONF.register_opts(api_opts, group='api')


def setup_app():
    root_app = flask.Flask('cloudkitty')
    root_api = flask_restful.Api(root_app)
    root_api.add_resource(api_root.CloudkittyAPIRoot, '/')

    dispatch_dict = {
        '/v1': get_v1_app(),
        '/v2': get_v2_app(),
    }

    # Disabling v2 api in case v1 storage is used
    if CONF.storage.version < 2:
        LOG.warning('v1 storage is used, disabling v2 API')
        dispatch_dict.pop('/v2')

    app = dispatcher.DispatcherMiddleware(root_app, dispatch_dict)
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
    LOG.info("Cloudkitty API with '%s' auth type will be loaded.",
             cfg.CONF.auth_strategy)
    return deploy.loadapp("config:" + cfg_file, name=appname)


def build_wsgi_app(argv=None):
    service.prepare_service()
    return load_app()


def app_factory(global_config, **local_conf):
    return setup_app()
