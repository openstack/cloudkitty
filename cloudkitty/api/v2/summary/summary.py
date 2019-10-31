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
from cloudkitty.utils import tz as tzutils


class Summary(base.BaseResource):
    """Resource allowing to retrieve a rating summary."""

    @api_utils.paginated
    @api_utils.add_input_schema('query', {
        voluptuous.Optional('groupby'): api_utils.MultiQueryParam(str),
        voluptuous.Optional('filters'):
            api_utils.SingleDictQueryParam(str, str),
        voluptuous.Optional('begin'): api_utils.SingleQueryParam(
            tzutils.dt_from_iso),
        voluptuous.Optional('end'): api_utils.SingleQueryParam(
            tzutils.dt_from_iso),
    })
    def get(self, groupby=None, filters={},
            begin=None, end=None,
            offset=0, limit=100):
        policy.authorize(
            flask.request.context,
            'summary:get_summary',
            {'project_id': flask.request.context.project_id})
        begin = begin or tzutils.get_month_start()
        end = end or tzutils.get_next_month()

        if not flask.request.context.is_admin:
            if flask.request.context.project_id is None:
                # Unscoped non-admin user
                return {
                    'total': 0,
                    'columns': [],
                    'results': [],
                }
            filters['project_id'] = flask.request.context.project_id

        metric_types = [filters.pop('type')] if 'type' in filters else None
        total = self._storage.total(
            begin=begin, end=end,
            groupby=groupby,
            filters=filters,
            metric_types=metric_types,
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
