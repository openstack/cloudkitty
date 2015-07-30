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
import hashlib
import zlib

from oslo_db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative
from sqlalchemy.ext import hybrid

Base = declarative.declarative_base()


class PyScriptsBase(models.ModelBase):
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    fk_to_resolve = {}

    def save(self, session=None):
        from cloudkitty import db

        if session is None:
            session = db.get_session()

        super(PyScriptsBase, self).save(session=session)

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            if c.name == 'id':
                continue
            d[c.name] = self[c.name]
        return d

    def _recursive_resolve(self, path):
        obj = self
        for attr in path.split('.'):
            if hasattr(obj, attr):
                obj = getattr(obj, attr)
            else:
                return None
        return obj

    def export_model(self):
        res = self.as_dict()
        for fk, mapping in self.fk_to_resolve.items():
            res[fk] = self._recursive_resolve(mapping)
        return res


class PyScriptsScript(Base, PyScriptsBase):
    """A PyScripts entry.

    """
    __tablename__ = 'pyscripts_scripts'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    script_id = sqlalchemy.Column(sqlalchemy.String(36),
                                  nullable=False,
                                  unique=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=False,
        unique=True)
    _data = sqlalchemy.Column('data',
                              sqlalchemy.LargeBinary(),
                              nullable=False)
    _checksum = sqlalchemy.Column('checksum',
                                  sqlalchemy.String(40),
                                  nullable=False)

    @hybrid.hybrid_property
    def data(self):
        udata = zlib.decompress(self._data)
        return udata

    @data.setter
    def data(self, value):
        sha_check = hashlib.sha1()
        sha_check.update(value)
        self._checksum = sha_check.hexdigest()
        self._data = zlib.compress(value)

    @hybrid.hybrid_property
    def checksum(self):
        return self._checksum

    def __repr__(self):
        return ('<PyScripts Script[{uuid}]: '
                'name={name}>').format(
                    uuid=self.script_id,
                    name=self.name)
