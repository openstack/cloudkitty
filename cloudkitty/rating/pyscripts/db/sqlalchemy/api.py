# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
from oslo_db import exception
from oslo_db.sqlalchemy import utils
from oslo_utils import uuidutils
import sqlalchemy

from cloudkitty import db
from cloudkitty.rating.pyscripts.db import api
from cloudkitty.rating.pyscripts.db.sqlalchemy import migration
from cloudkitty.rating.pyscripts.db.sqlalchemy import models


def get_backend():
    return PyScripts()


class PyScripts(api.PyScripts):

    def get_migration(self):
        return migration

    def get_script(self, name=None, uuid=None):
        session = db.get_session()
        try:
            q = session.query(models.PyScriptsScript)
            if name:
                q = q.filter(
                    models.PyScriptsScript.name == name)
            elif uuid:
                q = q.filter(
                    models.PyScriptsScript.script_id == uuid)
            else:
                raise ValueError('You must specify either name or uuid.')
            res = q.one()
            return res
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchScript(name=name, uuid=uuid)

    def list_scripts(self):
        session = db.get_session()
        q = session.query(models.PyScriptsScript)
        res = q.values(
            models.PyScriptsScript.script_id)
        return [uuid[0] for uuid in res]

    def create_script(self, name, data):
        session = db.get_session()
        try:
            with session.begin():
                script_db = models.PyScriptsScript(name=name)
                script_db.data = data
                script_db.script_id = uuidutils.generate_uuid()
                session.add(script_db)
            return script_db
        except exception.DBDuplicateEntry:
            script_db = self.get_script(name=name)
            raise api.ScriptAlreadyExists(
                script_db.name,
                script_db.script_id)

    def update_script(self, uuid, **kwargs):
        session = db.get_session()
        try:
            with session.begin():
                q = session.query(models.PyScriptsScript)
                q = q.filter(
                    models.PyScriptsScript.script_id == uuid
                )
                script_db = q.with_lockmode('update').one()
                if kwargs:
                    excluded_cols = ['script_id']
                    for col in excluded_cols:
                        if col in kwargs:
                            kwargs.pop(col)
                    for attribute, value in kwargs.items():
                        if hasattr(script_db, attribute):
                            setattr(script_db, attribute, value)
                        else:
                            raise ValueError('No such attribute: {}'.format(
                                attribute))
                else:
                    raise ValueError('No attribute to update.')
                return script_db
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchScript(uuid=uuid)

    def delete_script(self, name=None, uuid=None):
        session = db.get_session()
        q = utils.model_query(
            models.PyScriptsScript,
            session)
        if name:
            q = q.filter(models.PyScriptsScript.name == name)
        elif uuid:
            q = q.filter(models.PyScriptsScript.script_id == uuid)
        else:
            raise ValueError('You must specify either name or uuid.')
        r = q.delete()
        if not r:
            raise api.NoSuchScript(uuid=uuid)
