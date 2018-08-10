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
from oslo_db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative


Base = declarative.declarative_base()


class IdentifierState(Base, models.ModelBase):
    """Represents the state of a given identifier."""
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    __tablename__ = 'cloudkitty_storage_states'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    # SHA1 of the identifier
    identifier = sqlalchemy.Column(sqlalchemy.String(256),
                                   nullable=False,
                                   unique=True)
    state = sqlalchemy.Column(sqlalchemy.DateTime,
                              nullable=False)
