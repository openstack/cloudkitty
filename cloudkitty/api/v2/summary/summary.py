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

from cloudkitty.api.v2 import base
from cloudkitty.api.v2 import utils as api_utils
from cloudkitty.common import policy
from cloudkitty import utils


class Summary(base.BaseResource):
    """Resource allowing to retrieve a rating summary."""

    @api_utils.paginated
    @api_utils.add_input_schema('query', {
        voluptuous.Optional('groupby'): api_utils.MultiQueryParam(str),
        voluptuous.Optional('filters'):
            api_utils.SingleDictQueryParam(str, str),
        voluptuous.Optional('begin'): voluptuous.Coerce(utils.iso2dt),
        voluptuous.Optional('end'): voluptuous.Coerce(utils.iso2dt),
    })
    def get(self, groupby=None, filters={},
            begin=None, end=None,
            offset=0, limit=100):
        policy.authorize(
            flask.request.context,
            'summary:get_summary',
            {'tenant_id': flask.request.context.project_id})
        begin = begin or utils.get_month_start()
        end = end or utils.get_next_month()

        if not flask.request.context.is_admin:
            filters['project_id'] = flask.request.context.project_id

        total = self._storage.total(
            begin=begin, end=end,
            groupby=groupby,
            filters=filters,
            offset=offset,
            limit=limit,
            paginate=True,
        )
        columns = []
        if len(total['results']) > 0:
            columns = list(total['results'][0].keys())

        return {
            'total': total['total'],
            'columns': columns,
            'results': [list(res.values()) for res in total['results']]
        }
