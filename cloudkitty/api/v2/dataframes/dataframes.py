# Copyright 2019 Objectif Libre
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
import voluptuous
from werkzeug import exceptions as http_exceptions

from cloudkitty.api.v2 import base
from cloudkitty.api.v2 import utils as api_utils
from cloudkitty.common import policy
from cloudkitty import dataframe


class DataFrameList(base.BaseResource):
    @api_utils.add_input_schema('body', {
        voluptuous.Required('dataframes'): [dataframe.DataFrame.from_dict],
    })
    def post(self, dataframes=[]):
        policy.authorize(
            flask.request.context,
            'dataframes:add',
            {},
        )

        if not dataframes:
            raise http_exceptions.BadRequest(
                "Parameter dataframes must not be empty.")

        self._storage.push(dataframes)

        return {}, 204
