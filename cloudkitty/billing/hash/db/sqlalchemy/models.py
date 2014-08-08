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
from oslo.db.sqlalchemy import models
import sqlalchemy
from sqlalchemy.ext import declarative
from sqlalchemy import orm
from sqlalchemy import schema


Base = declarative.declarative_base()


class HashMapBase(models.ModelBase):
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}


class HashMapService(Base, HashMapBase):
    """An hashmap service.

    """

    __tablename__ = 'hashmap_services'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=False,
        unique=True
    )
    fields = orm.relationship('HashMapField')

    def __repr__(self):
        return ('<HashMapService[{id}]: '
                'service={service}>').format(
                    id=self.id,
                    service=self.name)


class HashMapField(Base, HashMapBase):
    """An hashmap field.

    """

    __tablename__ = 'hashmap_fields'

    @declarative.declared_attr
    def __table_args__(cls):
        args = (schema.UniqueConstraint('service_id', 'name',
                                        name='uniq_map_service_field'),
                HashMapBase.__table_args__,)
        return args

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String(255),
                             nullable=False)
    service_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey('hashmap_services.id',
                              ondelete='CASCADE'),
        nullable=False
    )
    field_maps = orm.relationship('HashMapMapping')

    def __repr__(self):
        return ('<HashMapField[{id}]: '
                'field={field}>').format(
                    id=self.id,
                    field=self.field)


class HashMapMapping(Base, HashMapBase):
    """A mapping between a field a value and a type.

    """

    __tablename__ = 'hashmap_maps'

    @declarative.declared_attr
    def __table_args__(cls):
        args = (schema.UniqueConstraint('key', 'field_id',
                                        name='uniq_mapping'),
                HashMapBase.__table_args__,)
        return args

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True)
    key = sqlalchemy.Column(sqlalchemy.String(255),
                            nullable=False)
    value = sqlalchemy.Column(sqlalchemy.Float,
                              nullable=False)
    map_type = sqlalchemy.Column(sqlalchemy.Enum('flat',
                                                 'rate',
                                                 name='enum_map_type'),
                                 nullable=False)
    field_id = sqlalchemy.Column(sqlalchemy.Integer,
                                 sqlalchemy.ForeignKey('hashmap_fields.id',
                                                       ondelete='CASCADE'),
                                 nullable=False)

    def __repr__(self):
        return ('<HashMapMapping[{id}]: '
                'type={map_type} {key}={value}>').format(
                    id=self.id,
                    map_type=self.map_type,
                    key=self.key,
                    value=self.value)
