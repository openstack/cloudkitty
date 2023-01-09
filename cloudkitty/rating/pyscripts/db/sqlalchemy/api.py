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
import datetime

from oslo_db import exception
from oslo_utils import uuidutils
import sqlalchemy

from cloudkitty import db
from cloudkitty.rating.common.db.filters import get_filters
from cloudkitty.rating.pyscripts.db import api
from cloudkitty.rating.pyscripts.db.sqlalchemy import migration
from cloudkitty.rating.pyscripts.db.sqlalchemy import models


def get_backend():
    return PyScripts()


class PyScripts(api.PyScripts):

    def get_migration(self):
        return migration

    def get_script(self, name=None, uuid=None, deleted=False):
        with db.session_for_read() as session:
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
                if not deleted:
                    q = q.filter(
                        models.PyScriptsScript.deleted == sqlalchemy.null())
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchScript(name=name, uuid=uuid)

    def list_scripts(self, **kwargs):
        with db.session_for_read() as session:
            q = session.query(models.PyScriptsScript)
            q = get_filters(q, models.PyScriptsScript, **kwargs)
            res = q.values(
                models.PyScriptsScript.script_id)
            return [uuid[0] for uuid in res]

    def create_script(self, name, data,
                      start=None,
                      end=None,
                      description=None,
                      created_by=None):
        created_at = datetime.datetime.now()
        try:
            with db.session_for_write() as session:
                q = session.query(models.PyScriptsScript)
                q = q.filter(
                    models.PyScriptsScript.name == name,
                    models.PyScriptsScript.deleted == sqlalchemy.null()
                )
                script_db = q.with_for_update().all()
                if script_db:
                    script_db = self.get_script(name=name)
                    raise api.ScriptAlreadyExists(
                        script_db.name,
                        script_db.script_id)
                script_db = models.PyScriptsScript(
                    name=name,
                    start=start,
                    created_at=created_at,
                    end=end,
                    description=description,
                    deleted=None,
                    created_by=created_by,
                    updated_by=None,
                    deleted_by=None)
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
        try:
            with db.session_for_write() as session:
                q = session.query(models.PyScriptsScript)
                q = q.filter(
                    models.PyScriptsScript.script_id == uuid,
                    models.PyScriptsScript.deleted == sqlalchemy.null()
                )
                script_db = q.with_for_update().one()
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

    def delete_script(self, name=None, uuid=None, deleted_by=None):
        with db.session_for_write() as session:
            try:
                q = session.query(models.PyScriptsScript)
                if name:
                    q = q.filter(models.PyScriptsScript.name == name)
                elif uuid:
                    q = q.filter(models.PyScriptsScript.script_id == uuid)
                else:
                    raise ValueError(
                        'You must specify either name or uuid.')
                q = q.filter(
                    models.PyScriptsScript.deleted == sqlalchemy.null())

                script_db = q.with_for_update().one()
                script_db.deleted_by = deleted_by
                script_db.deleted = datetime.datetime.now()
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchScript(uuid=uuid)
