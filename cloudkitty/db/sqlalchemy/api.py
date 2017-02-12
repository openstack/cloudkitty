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
from oslo_db.sqlalchemy import utils
import sqlalchemy

from cloudkitty import config  # NOQA
from cloudkitty import db
from cloudkitty.db import api
from cloudkitty.db.sqlalchemy import migration
from cloudkitty.db.sqlalchemy import models


def get_backend():
    return DBAPIManager


class State(api.State):

    def get_state(self, name):
        session = db.get_session()
        q = utils.model_query(
            models.StateInfo,
            session)
        q = q.filter(models.StateInfo.name == name)
        return q.value(models.StateInfo.state)

    def set_state(self, name, state):
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.StateInfo,
                    session)
                q = q.filter(models.StateInfo.name == name)
                q = q.with_lockmode('update')
                db_state = q.one()
                db_state.state = state
            except sqlalchemy.orm.exc.NoResultFound:
                db_state = models.StateInfo(name=name,
                                            state=state)
                session.add(db_state)
        return db_state.state

    def get_metadata(self, name):
        session = db.get_session()
        q = utils.model_query(
            models.StateInfo,
            session)
        q.filter(models.StateInfo.name == name)
        return q.value(models.StateInfo.s_metadata)

    def set_metadata(self, name, metadata):
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.StateInfo,
                    session)
                q = q.filter(models.StateInfo.name == name)
                q = q.with_lockmode('update')
                db_state = q.one()
                db_state.s_metadata = metadata
            except sqlalchemy.orm.exc.NoResultFound:
                db_state = models.StateInfo(name=name,
                                            s_metadata=metadata)
                session.add(db_state)


class ModuleInfo(api.ModuleInfo):
    """Base class for module info management."""

    def get_priority(self, name):
        session = db.get_session()
        q = utils.model_query(
            models.ModuleStateInfo,
            session)
        q = q.filter(models.ModuleStateInfo.name == name)
        res = q.value(models.ModuleStateInfo.priority)
        if res:
            return int(res)
        else:
            return 1

    def set_priority(self, name, priority):
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.ModuleStateInfo,
                    session)
                q = q.filter(
                    models.ModuleStateInfo.name == name)
                q = q.with_lockmode('update')
                db_state = q.one()
                db_state.priority = priority
            except sqlalchemy.orm.exc.NoResultFound:
                db_state = models.ModuleStateInfo(name=name,
                                                  priority=priority)
                session.add(db_state)
        return int(db_state.priority)

    def get_state(self, name):
        session = db.get_session()
        try:
            q = utils.model_query(
                models.ModuleStateInfo,
                session)
            q = q.filter(models.ModuleStateInfo.name == name)
            res = q.value(models.ModuleStateInfo.state)
            return bool(res)
        except sqlalchemy.orm.exc.NoResultFound:
            return None

    def set_state(self, name, state):
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.ModuleStateInfo,
                    session)
                q = q.filter(models.ModuleStateInfo.name == name)
                q = q.with_lockmode('update')
                db_state = q.one()
                db_state.state = state
            except sqlalchemy.orm.exc.NoResultFound:
                db_state = models.ModuleStateInfo(name=name, state=state)
                session.add(db_state)
        return bool(db_state.state)


class ServiceToCollectorMapping(object):
    """Base class for service to collector mapping."""

    def get_mapping(self, service):
        session = db.get_session()
        try:
            q = utils.model_query(
                models.ServiceToCollectorMapping,
                session)
            q = q.filter(
                models.ServiceToCollectorMapping.service == service)
            return q.one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchMapping(service)

    def set_mapping(self, service, collector):
        session = db.get_session()
        with session.begin():
            try:
                q = utils.model_query(
                    models.ServiceToCollectorMapping,
                    session)
                q = q.filter(
                    models.ServiceToCollectorMapping.service == service)
                q = q.with_lockmode('update')
                db_mapping = q.one()
                db_mapping.collector = collector
            except sqlalchemy.orm.exc.NoResultFound:
                model = models.ServiceToCollectorMapping
                db_mapping = model(service=service,
                                   collector=collector)
                session.add(db_mapping)
        return db_mapping

    def list_services(self, collector=None):
        session = db.get_session()
        q = utils.model_query(
            models.ServiceToCollectorMapping,
            session)
        if collector:
            q = q.filter(
                models.ServiceToCollectorMapping.collector == collector)
        res = q.distinct().values(
            models.ServiceToCollectorMapping.service)
        return res

    def list_mappings(self, collector=None):
        session = db.get_session()
        q = utils.model_query(
            models.ServiceToCollectorMapping,
            session)
        if collector:
            q = q.filter(
                models.ServiceToCollectorMapping.collector == collector)
        res = q.all()
        return res

    def delete_mapping(self, service):
        session = db.get_session()
        q = utils.model_query(
            models.ServiceToCollectorMapping,
            session)
        q = q.filter(models.ServiceToCollectorMapping.service == service)
        r = q.delete()
        if not r:
            raise api.NoSuchMapping(service)


class DBAPIManager(object):

    @staticmethod
    def get_state():
        return State()

    @staticmethod
    def get_module_info():
        return ModuleInfo()

    @staticmethod
    def get_service_to_collector_mapping():
        return ServiceToCollectorMapping()

    @staticmethod
    def get_migration():
        return migration
