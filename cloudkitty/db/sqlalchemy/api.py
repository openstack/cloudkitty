# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
# @author: Stéphane Albert
#
from oslo.config import cfg
from oslo.db.sqlalchemy import utils
import sqlalchemy

from cloudkitty import config  # NOQA
from cloudkitty import db
from cloudkitty.db import api
from cloudkitty.db.sqlalchemy import models
from cloudkitty.openstack.common import log as logging

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def get_backend():
    return DBAPIManager


class State(api.State):

    def get_state(self, name):
        session = db.get_session()
        try:
            return bool(utils.model_query(
                models.StateInfo,
                session
            ).filter_by(
                name=name,
            ).value('state'))
        except sqlalchemy.orm.exc.NoResultFound:
            return None

    def set_state(self, name, state):
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.StateInfo,
                    session
                ).filter_by(
                    name=name,
                ).with_lockmode('update')
                db_state = q.one()
                db_state.state = state
            except sqlalchemy.orm.exc.NoResultFound:
                db_state = models.StateInfo(name=name, state=state)
                session.add(db_state)
        return bool(db_state.state)

    def get_metadata(self, name):
        session = db.get_session()
        return utils.model_query(
            models.StateInfo,
            session
        ).filter_by(
            name=name,
        ).value('s_metadata')

    def set_metadata(self, name, metadata):
        session = db.get_session()
        try:
            db_state = utils.model_query(
                models.StateInfo,
                session
            ).filter_by(
                name=name,
            ).with_lockmode('update').one()
            db_state.s_metadata = metadata
        except sqlalchemy.orm.exc.NoResultFound:
            db_state = models.StateInfo(name=name, s_metadata=metadata)
            session.add(db_state)
        finally:
            session.flush()


class DBAPIManager(object):

    @staticmethod
    def get_state():
        return State()
