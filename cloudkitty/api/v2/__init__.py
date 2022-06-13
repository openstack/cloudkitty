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
import voluptuous

from cloudkitty.common import context


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
    'cloudkitty.api.v2.dataframes',
    'cloudkitty.api.v2.summary',
    'cloudkitty.api.v2.task',
    'cloudkitty.api.v2.rating',
]


def _extend_request_context():
    flask.request.context = context.RequestContext.from_environ(
        flask.request.environ)


def get_api_app():
    app = flask.Flask(__name__)
    for module_name in API_MODULES:
        module = importlib.import_module(module_name)
        module.init(app)
    app.before_request(_extend_request_context)
    return app
