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
import importlib

import flask
from oslo_context import context
import voluptuous

from cloudkitty.common import policy


RESOURCE_SCHEMA = voluptuous.Schema({
    # python module containing the resource
    voluptuous.Required('module'): str,
    # Name of the resource class
    voluptuous.Required('resource_class'): str,
    # Url suffix of this specific resource
    voluptuous.Required('url'): str,
})


API_MODULES = [
    'cloudkitty.api.v2.scope',
    'cloudkitty.api.v2.summary',
]


def _extend_request_context():
    headers = flask.request.headers

    roles = headers.get('X-Roles', '').split(',')
    is_admin = policy.check_is_admin(roles)

    ctx = {
        'user_id': headers.get('X-User-Id', ''),
        'auth_token': headers.get('X-Auth-Token', ''),
        'is_admin': is_admin,
        'roles': roles,
        'project_id': headers.get('X-Project-Id', ''),
        'domain_id': headers.get('X-Domain-Id', ''),
    }

    flask.request.context = context.RequestContext(**ctx)


def get_api_app():
    app = flask.Flask(__name__)
    for module_name in API_MODULES:
        module = importlib.import_module(module_name)
        module.init(app)
    app.before_request(_extend_request_context)
    return app
