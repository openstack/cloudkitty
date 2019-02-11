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
import flask
import flask_restful
import voluptuous
from werkzeug import exceptions as http_exceptions

from cloudkitty.api.v2 import utils as api_utils
from cloudkitty.common import policy


class Example(flask_restful.Resource):

    @api_utils.add_output_schema({
        voluptuous.Required(
            'message',
            default='This is an example endpoint',
        ): api_utils.get_string_type(),
    })
    def get(self):
        policy.authorize(flask.request.context, 'example:get_example', {})
        return {}

    @api_utils.add_input_schema('query', {
        voluptuous.Required('fruit'): api_utils.SingleQueryParam(str),
    })
    def put(self, fruit=None):
        policy.authorize(flask.request.context, 'example:submit_fruit', {})
        if not fruit:
            raise http_exceptions.BadRequest(
                'You must submit a fruit',
            )
        if fruit not in ['banana', 'strawberry']:
            raise http_exceptions.Forbidden(
                'You submitted a forbidden fruit',
            )
        return {
            'message': 'Your fruit is a ' + fruit,
        }

    @api_utils.add_input_schema('body', {
        voluptuous.Required('fruit'): api_utils.get_string_type(),
    })
    def post(self, fruit=None):
        policy.authorize(flask.request.context, 'example:submit_fruit', {})
        if not fruit:
            raise http_exceptions.BadRequest(
                'You must submit a fruit',
            )
        if fruit not in ['banana', 'strawberry']:
            raise http_exceptions.Forbidden(
                'You submitted a forbidden fruit',
            )
        return {
            'message': 'Your fruit is a ' + fruit,
        }
