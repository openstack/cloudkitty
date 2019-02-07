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
from oslo_config import cfg
from oslo_db.sqlalchemy import utils
from oslo_log import log

from cloudkitty import db
from cloudkitty.storage_state import migration
from cloudkitty.storage_state import models
from cloudkitty import utils as ck_utils


LOG = log.getLogger(__name__)


CONF = cfg.CONF
# NOTE(peschk_l): Required for defaults
CONF.import_opt('backend', 'cloudkitty.fetcher', 'fetcher')
CONF.import_opt('collector', 'cloudkitty.collector', 'collect')
CONF.import_opt('scope_key', 'cloudkitty.collector', 'collect')


class StateManager(object):
    """Class allowing state management in CloudKitty"""

    model = models.IdentifierState

    def _get_db_item(self, session, identifier,
                     fetcher=None, collector=None, scope_key=None):
        fetcher = fetcher or CONF.fetcher.backend
        collector = collector or CONF.collect.collector
        scope_key = scope_key or CONF.collect.scope_key

        q = utils.model_query(self.model, session)
        r = q.filter(self.model.identifier == identifier). \
            filter(self.model.scope_key == scope_key). \
            filter(self.model.fetcher == fetcher). \
            filter(self.model.collector == collector). \
            first()

        # In case the identifier exists with empty columns, update them
        if not r:
            # NOTE(peschk_l): We must use == instead of 'is' because sqlachmey
            # overloads this operator
            r = q.filter(self.model.identifier == identifier). \
                filter(self.model.scope_key == None). \
                filter(self.model.fetcher == None). \
                filter(self.model.collector == None). \
                first()  # noqa
            if r:
                r.scope_key = scope_key
                r.collector = collector
                r.fetcher = fetcher
                LOG.info('Updating identifier "{i}" with scope_key "{sk}", '
                         'collector "{c}" and fetcher "{f}"'.format(
                             i=identifier,
                             sk=scope_key,
                             c=collector,
                             f=fetcher))
                session.commit()
        return r

    def set_state(self, identifier, state,
                  fetcher=None, collector=None, scope_key=None):
        if isinstance(state, int):
            state = ck_utils.ts2dt(state)
        session = db.get_session()
        session.begin()
        r = self._get_db_item(
            session, identifier, fetcher, collector, scope_key)
        if r and r.state != state:
            r.state = state
            session.commit()
        else:
            state_object = self.model(
                identifier=identifier,
                state=state,
                fetcher=fetcher,
                collector=collector,
                scope_key=scope_key,
            )
            session.add(state_object)
            session.commit()
        session.close()

    def get_state(self, identifier,
                  fetcher=None, collector=None, scope_key=None):
        session = db.get_session()
        session.begin()
        r = self._get_db_item(
            session, identifier, fetcher, collector, scope_key)
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
