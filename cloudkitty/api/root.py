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
from flask import request
from oslo_config import cfg
import voluptuous

from cloudkitty.api.v2 import base
from cloudkitty.api.v2 import utils as api_utils


CONF = cfg.CONF
CONF.import_opt('version', 'cloudkitty.storage', 'storage')

API_VERSION_SCHEMA = voluptuous.Schema({
    voluptuous.Required('id'): str,
    voluptuous.Required('links'): [
        voluptuous.Schema({
            voluptuous.Required('href'): str,
            voluptuous.Required('rel', default='self'): 'self',
        }),
    ],
    voluptuous.Required('status'): voluptuous.Any(
        'CURRENT',
        'SUPPORTED',
        'EXPERIMENTAL',
        'DEPRECATED',
    ),
})


def get_api_versions():
    """Returns a list of all existing API versions."""
    apis = [
        {
            'id': 'v1',
            'links': [{
                'href': '{scheme}://{host}/v1'.format(
                    scheme=request.scheme,
                    host=request.host,
                ),
            }],
            'status': 'CURRENT',
        },
        {
            'id': 'v2',
            'links': [{
                'href': '{scheme}://{host}/v2'.format(
                    scheme=request.scheme,
                    host=request.host,
                ),
            }],
            'status': 'EXPERIMENTAL',
        },
    ]

    # v2 api is disabled when using v1 storage
    if CONF.storage.version < 2:
        apis = apis[:1]

    return apis


class CloudkittyAPIRoot(base.BaseResource):

    @api_utils.add_output_schema(voluptuous.Schema({
        'versions': [API_VERSION_SCHEMA],
    }))
    def get(self):
        return {
            'versions': get_api_versions(),
        }
