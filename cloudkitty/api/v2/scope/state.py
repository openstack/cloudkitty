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

from oslo_log import log

LOG = log.getLogger(__name__)


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
        voluptuous.Optional('active', default=[]):
            api_utils.MultiQueryParam(int),
    })
    @api_utils.add_output_schema({'results': [{
        voluptuous.Required('scope_id'): vutils.get_string_type(),
        voluptuous.Required('scope_key'): vutils.get_string_type(),
        voluptuous.Required('fetcher'): vutils.get_string_type(),
        voluptuous.Required('collector'): vutils.get_string_type(),
        voluptuous.Optional(
            'last_processed_timestamp'): vutils.get_string_type(),
        voluptuous.Required('active'): bool,
        voluptuous.Optional('scope_activation_toggle_date'):
            vutils.get_string_type(),
    }]})
    def get(self, offset=0, limit=100, scope_id=None, scope_key=None,
            fetcher=None, collector=None, active=None):

        policy.authorize(
            flask.request.context,
            'scope:get_state',
            {'project_id': scope_id or flask.request.context.project_id}
        )
        results = self._storage_state.get_all(
            identifier=scope_id, scope_key=scope_key, fetcher=fetcher,
            collector=collector, offset=offset, limit=limit, active=active)

        if len(results) < 1:
            raise http_exceptions.NotFound(
                "No resource found for provided filters.")
        return {
            'results': [{
                'scope_id': r.identifier,
                'scope_key': r.scope_key,
                'fetcher': r.fetcher,
                'collector': r.collector,
                'last_processed_timestamp':
                    r.last_processed_timestamp.isoformat(),
                'active': r.active,
                'scope_activation_toggle_date':
                    r.scope_activation_toggle_date.isoformat() if
                    r.scope_activation_toggle_date else None
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
        voluptuous.Optional('last_processed_timestamp'):
            voluptuous.Coerce(tzutils.dt_from_iso),
    })
    def put(self,
            all_scopes=False,
            scope_id=None,
            scope_key=None,
            fetcher=None,
            collector=None,
            last_processed_timestamp=None):

        policy.authorize(
            flask.request.context,
            'scope:reset_state',
            {'project_id': scope_id or flask.request.context.project_id}
        )

        if not all_scopes and scope_id is None:
            raise http_exceptions.BadRequest(
                "Either all_scopes or a scope_id should be specified.")

        if not last_processed_timestamp:
            raise http_exceptions.BadRequest(
                "Variable 'last_processed_timestamp' cannot be empty/None.")

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
            'scopes': serialized_results,
            'last_processed_timestamp': last_processed_timestamp.isoformat()
        })

        return {}, 202

    @api_utils.add_input_schema('body', {
        voluptuous.Required('scope_id'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('scope_key'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('fetcher'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('collector'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('active'):
            api_utils.SingleQueryParam(bool),
    })
    @api_utils.add_output_schema({
        voluptuous.Required('scope_id'): vutils.get_string_type(),
        voluptuous.Required('scope_key'): vutils.get_string_type(),
        voluptuous.Required('fetcher'): vutils.get_string_type(),
        voluptuous.Required('collector'): vutils.get_string_type(),
        voluptuous.Optional('last_processed_timestamp'):
            voluptuous.Coerce(tzutils.dt_from_iso),
        voluptuous.Required('active'): bool,
        voluptuous.Required('scope_activation_toggle_date'):
            vutils.get_string_type()
    })
    def patch(self, scope_id, scope_key=None, fetcher=None,
              collector=None, active=None):

        policy.authorize(
            flask.request.context,
            'scope:patch_state',
            {'tenant_id': scope_id or flask.request.context.project_id}
        )
        results = self._storage_state.get_all(identifier=scope_id, active=None)

        if len(results) < 1:
            raise http_exceptions.NotFound(
                "No resource found for provided filters.")

        if len(results) > 1:
            LOG.debug("Too many resources found with the same scope_id [%s], "
                      "scopes found: [%s].", scope_id, results)
            raise http_exceptions.NotFound("Too many resources found with "
                                           "the same scope_id: %s." % scope_id)

        scope_to_update = results[0]
        LOG.debug("Executing update of storage scope: [%s].", scope_to_update)

        self._storage_state.update_storage_scope(scope_to_update,
                                                 scope_key=scope_key,
                                                 fetcher=fetcher,
                                                 collector=collector,
                                                 active=active)

        storage_scopes = self._storage_state.get_all(
            identifier=scope_id, active=active)
        update_storage_scope = storage_scopes[0]
        return {
            'scope_id': update_storage_scope.identifier,
            'scope_key': update_storage_scope.scope_key,
            'fetcher': update_storage_scope.fetcher,
            'collector': update_storage_scope.collector,
            'last_processed_timestamp':
                update_storage_scope.last_processed_timestamp.isoformat(),
            'active': update_storage_scope.active,
            'scope_activation_toggle_date':
                update_storage_scope.scope_activation_toggle_date.isoformat()
        }

    @api_utils.add_input_schema('body', {
        voluptuous.Required('scope_id'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('scope_key'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('fetcher'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('collector'):
            api_utils.SingleQueryParam(str),
        voluptuous.Optional('active'):
            api_utils.SingleQueryParam(bool),
    })
    @api_utils.add_output_schema({
        voluptuous.Required('scope_id'): vutils.get_string_type(),
        voluptuous.Required('scope_key'): vutils.get_string_type(),
        voluptuous.Required('fetcher'): vutils.get_string_type(),
        voluptuous.Required('collector'): vutils.get_string_type(),
        voluptuous.Optional('last_processed_timestamp'):
            voluptuous.Coerce(tzutils.dt_from_iso),
        voluptuous.Required('active'): bool,
        voluptuous.Required('scope_activation_toggle_date'):
            vutils.get_string_type()
    })
    def post(self, scope_id, scope_key=None, fetcher=None, collector=None,
             active=None):

        policy.authorize(
            flask.request.context,
            'scope:post_state',
            {'tenant_id': scope_id or flask.request.context.project_id}
        )
        results = self._storage_state.get_all(identifier=scope_id)

        if len(results) >= 1:
            LOG.debug("There is already a scope with ID [%s], "
                      "scopes found: [%s].", scope_id, results)
            raise http_exceptions.NotFound("Cannot create a scope with an "
                                           "already existing scope_id: %s."
                                           % scope_id)

        LOG.debug("Creating storage scope with data: [scope_id=%s, "
                  "scope_key=%s, fetcher=%s, collector=%s, active=%s].",
                  scope_id, scope_key, fetcher, collector, active)

        self._storage_state.create_scope(scope_id, None, fetcher=fetcher,
                                         collector=collector,
                                         scope_key=scope_key, active=active)

        storage_scopes = self._storage_state.get_all(
            identifier=scope_id)

        update_storage_scope = storage_scopes[0]
        last_processed_timestamp = None
        if update_storage_scope.last_processed_timestamp:
            last_processed_timestamp =\
                update_storage_scope.last_processed_timestamp.isoformat()

        return {
            'scope_id': update_storage_scope.identifier,
            'scope_key': update_storage_scope.scope_key,
            'fetcher': update_storage_scope.fetcher,
            'collector': update_storage_scope.collector,
            'last_processed_timestamp': last_processed_timestamp,
            'active': update_storage_scope.active,
            'scope_activation_toggle_date':
                update_storage_scope.scope_activation_toggle_date.isoformat()
        }
