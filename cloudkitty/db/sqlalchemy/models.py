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
from oslo_db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative


Base = declarative.declarative_base()


class StateInfo(Base, models.ModelBase):
    """State

    """

    __tablename__ = 'states'

    name = sqlalchemy.Column(sqlalchemy.String(255),
                             primary_key=True)
    state = sqlalchemy.Column(
        sqlalchemy.BigInteger(),
        nullable=False)
    s_metadata = sqlalchemy.Column(sqlalchemy.Text(),
                                   nullable=True,
                                   default='')

    def __repr__(self):
        return ('<StateInfo[{name}]: '
                'state={state} metadata={metadata}>').format(
                    name=self.name,
                    state=self.state,
                    metadata=self.s_metadata)


class ModuleStateInfo(Base, models.ModelBase):
    """Module state info.

    """

    __tablename__ = 'modules_state'

    name = sqlalchemy.Column(sqlalchemy.String(255),
                             primary_key=True)
    state = sqlalchemy.Column(
        sqlalchemy.Boolean(),
        nullable=False,
        default=False)
    priority = sqlalchemy.Column(
        sqlalchemy.Integer(),
        default=1)

    def __repr__(self):
        return ('<ModuleStateInfo[{name}]: '
                'enabled={state}>').format(
                    name=self.name,
                    state=self.state)

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


class ServiceToCollectorMapping(Base, models.ModelBase):
    """Collector module state.

    """

    __tablename__ = 'service_to_collector_mappings'

    service = sqlalchemy.Column(sqlalchemy.String(255),
                                primary_key=True)
    collector = sqlalchemy.Column(sqlalchemy.String(255),
                                  nullable=False)

    def __repr__(self):
        return ('<ServiceToCollectorMapping[{service}]: '
                'collector={collector}>').format(
                    service=self.service,
                    collector=self.collector)

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d
