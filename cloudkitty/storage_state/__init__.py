# -*- coding: utf-8 -*-
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
# @author: Luka Peschke
#
from oslo_db.sqlalchemy import utils

from cloudkitty import db
from cloudkitty.storage_state import migration
from cloudkitty.storage_state import models
from cloudkitty import utils as ck_utils


class StateManager(object):
    """Class allowing state management in CloudKitty"""

    model = models.IdentifierState

    def _get_db_item(self, session, identifier):
        q = utils.model_query(self.model, session)
        return q.filter(self.model.identifier == identifier).first()

    def set_state(self, identifier, state):
        if isinstance(state, int):
            state = ck_utils.ts2dt(state)
        session = db.get_session()
        session.begin()
        r = self._get_db_item(session, identifier)
        if r and r.state != state:
            r.state = state
            session.commit()
        else:
            state_object = self.model(
                identifier=identifier,
                state=state,
            )
            session.add(state_object)
            session.commit()
        session.close()

    def get_state(self, identifier):
        session = db.get_session()
        session.begin()
        r = self._get_db_item(session, identifier)
        session.close()
        return ck_utils.dt2ts(r.state) if r else None

    def init(self):
        migration.upgrade('head')

    # This is made in order to stay compatible with legacy behavior but
    # shouldn't be used
    def get_tenants(self, begin=None, end=None):
        session = db.get_session()
        session.begin()
        q = utils.model_query(self.model, session)
        session.close()
        return [tenant.identifier for tenant in q]
