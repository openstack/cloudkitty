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
from oslo_config import cfg
import voluptuous
from werkzeug import exceptions as http_exceptions

from cloudkitty.api.v2 import base
from cloudkitty.api.v2 import utils as api_utils
from cloudkitty.common import policy
from cloudkitty import dataframe
from cloudkitty.utils import tz as tzutils


CONF = cfg.CONF

CONF.import_opt('scope_key', 'cloudkitty.collector', 'collect')


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

    @api_utils.paginated
    @api_utils.add_input_schema('query', {
        voluptuous.Optional('begin'):
            api_utils.SingleQueryParam(tzutils.dt_from_iso),
        voluptuous.Optional('end'):
            api_utils.SingleQueryParam(tzutils.dt_from_iso),
        voluptuous.Optional('filters'):
            api_utils.SingleDictQueryParam(str, str),
    })
    @api_utils.add_output_schema({
        voluptuous.Required('total'): int,
        voluptuous.Required('dataframes'):
            [dataframe.DataFrame.as_dict],
    })
    def get(self,
            offset=0,
            limit=100,
            begin=None,
            end=None,
            filters=None):

        policy.authorize(
            flask.request.context,
            'dataframes:get',
            {'project_id': flask.request.context.project_id},
        )

        begin = begin or tzutils.get_month_start()
        end = end or tzutils.get_next_month()

        if filters and 'type' in filters:
            metric_types = [filters.pop('type')]
        else:
            metric_types = None

        if not flask.request.context.is_admin:
            if flask.request.context.project_id is None:
                # Unscoped non-admin user
                return {
                    'total': 0,
                    'dataframes': []
                }
            scope_key = CONF.collect.scope_key
            if filters:
                filters[scope_key] = flask.request.context.project_id
            else:
                filters = {scope_key: flask.request.context.project_id}

        results = self._storage.retrieve(
            begin=begin, end=end,
            filters=filters,
            metric_types=metric_types,
            offset=offset, limit=limit,
        )

        if results['total'] < 1:
            raise http_exceptions.NotFound(
                "No resource found for provided filters.")

        return {
            'total': results['total'],
            'dataframes': results['dataframes'],
        }
