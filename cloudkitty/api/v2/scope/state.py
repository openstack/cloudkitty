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
from cloudkitty import storage_state


class ScopeState(base.BaseResource):

    @api_utils.paginated
    @api_utils.add_input_schema('query', {
        voluptuous.Optional('scope_id', default=[]):
            api_utils.MultiQueryParam(str),
        voluptuous.Optional('scope_key', default=[]):
            api_utils.MultiQueryParam(str),
        voluptuous.Optional('fetcher', default=[]):
            api_utils.MultiQueryParam(str),
        voluptuous.Optional('collector', default=[]):
            api_utils.MultiQueryParam(str),
    })
    @api_utils.add_output_schema({'results': [{
        voluptuous.Required('scope_id'): api_utils.get_string_type(),
        voluptuous.Required('scope_key'): api_utils.get_string_type(),
        voluptuous.Required('fetcher'): api_utils.get_string_type(),
        voluptuous.Required('collector'): api_utils.get_string_type(),
        voluptuous.Required('state'): api_utils.get_string_type(),
    }]})
    def get(self,
            offset=0,
            limit=100,
            scope_id=None,
            scope_key=None,
            fetcher=None,
            collector=None):

        policy.authorize(
            flask.request.context,
            'scope:get_state',
            {'tenant_id': scope_id or flask.request.context.project_id}
        )
        results = storage_state.StateManager().get_all(
            identifier=scope_id,
            scope_key=scope_key,
            fetcher=fetcher,
            collector=collector,
            offset=offset,
            limit=limit,
        )
        if len(results) < 1:
            raise http_exceptions.NotFound(
                "No resource found for provided filters.")
        return {
            'results': [{
                'scope_id': r.identifier,
                'scope_key': r.scope_key,
                'fetcher': r.fetcher,
                'collector': r.collector,
                'state': str(r.state),
            } for r in results]
        }
