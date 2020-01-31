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
from cloudkitty import messaging
from cloudkitty import storage_state
from cloudkitty.utils import tz as tzutils
from cloudkitty.utils import validation as vutils


class ScopeState(base.BaseResource):

    @classmethod
    def reload(cls):
        super(ScopeState, cls).reload()
        cls._client = messaging.get_client()
        cls._storage_state = storage_state.StateManager()

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
        voluptuous.Required('scope_id'): vutils.get_string_type(),
        voluptuous.Required('scope_key'): vutils.get_string_type(),
        voluptuous.Required('fetcher'): vutils.get_string_type(),
        voluptuous.Required('collector'): vutils.get_string_type(),
        voluptuous.Required('state'): vutils.get_string_type(),
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
            {'project_id': scope_id or flask.request.context.project_id}
        )
        results = self._storage_state.get_all(
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
                'state': r.state.isoformat(),
            } for r in results]
        }

    @api_utils.add_input_schema('body', {
        voluptuous.Exclusive('all_scopes', 'scope_selector'):
            voluptuous.Boolean(),
        voluptuous.Exclusive('scope_id', 'scope_selector'):
            api_utils.MultiQueryParam(str),
        voluptuous.Optional('scope_key', default=[]):
            api_utils.MultiQueryParam(str),
        voluptuous.Optional('fetcher', default=[]):
            api_utils.MultiQueryParam(str),
        voluptuous.Optional('collector', default=[]):
            api_utils.MultiQueryParam(str),
        voluptuous.Required('state'):
            voluptuous.Coerce(tzutils.dt_from_iso),
    })
    def put(self,
            all_scopes=False,
            scope_id=None,
            scope_key=None,
            fetcher=None,
            collector=None,
            state=None):

        policy.authorize(
            flask.request.context,
            'scope:reset_state',
            {'project_id': scope_id or flask.request.context.project_id}
        )

        if not all_scopes and scope_id is None:
            raise http_exceptions.BadRequest(
                "Either all_scopes or a scope_id should be specified.")

        results = self._storage_state.get_all(
            identifier=scope_id,
            scope_key=scope_key,
            fetcher=fetcher,
            collector=collector,
        )

        if len(results) < 1:
            raise http_exceptions.NotFound(
                "No resource found for provided filters.")

        serialized_results = [{
            'scope_id': r.identifier,
            'scope_key': r.scope_key,
            'fetcher': r.fetcher,
            'collector': r.collector,
        } for r in results]

        self._client.cast({}, 'reset_state', res_data={
            'scopes': serialized_results, 'state': state.isoformat(),
        })

        return {}, 202
