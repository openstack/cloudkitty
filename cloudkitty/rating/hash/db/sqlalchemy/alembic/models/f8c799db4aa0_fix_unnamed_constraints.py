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
from sqlalchemy import orm
from sqlalchemy import schema

from cloudkitty.common.db import models as ck_models

Base = ck_models.get_base()


class HashMapBase(models.ModelBase):
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    fk_to_resolve = {}

    def save(self, session=None):
        from cloudkitty import db

        if session is None:
            session = db.get_session()

        super(HashMapBase, self).save(session=session)

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


class HashMapService(Base, HashMapBase):
    """A hashmap service.

    Used to describe a CloudKitty service such as compute or volume.
    """
    __tablename__ = 'hashmap_services'

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True)
    service_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        nullable=False,
        unique=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=False,
        unique=True)
    fields = orm.relationship(
        'HashMapField',
        backref=orm.backref(
            'service',
            lazy='immediate'))
    mappings = orm.relationship(
        'HashMapMapping',
        backref=orm.backref(
            'service',
            lazy='immediate'))
    thresholds = orm.relationship(
        'HashMapThreshold',
        backref=orm.backref(
            'service',
            lazy='immediate'))

    def __repr__(self):
        return ('<HashMapService[{uuid}]: '
                'service={service}>').format(
                    uuid=self.service_id,
                    service=self.name)


class HashMapField(Base, HashMapBase):
    """A hashmap field.

    Used to describe a service metadata such as flavor_id or image_id for
    compute.
    """
    __tablename__ = 'hashmap_fields'
    fk_to_resolve = {
        'service_id': 'service.service_id'}

    @declarative.declared_attr
    def __table_args__(cls):
        args = (
            schema.UniqueConstraint(
                'field_id',
                'name',
                name='uniq_field'),
            schema.UniqueConstraint(
                'service_id',
                'name',
                name='uniq_map_service_field'),
            HashMapBase.__table_args__,)
        return args

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True)
    field_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        nullable=False,
        unique=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=False)
    service_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_services.id',
            ondelete='CASCADE'),
        nullable=False)
    mappings = orm.relationship(
        'HashMapMapping',
        backref=orm.backref(
            'field',
            lazy='immediate'))
    thresholds = orm.relationship(
        'HashMapThreshold',
        backref=orm.backref(
            'field',
            lazy='immediate'))

    def __repr__(self):
        return ('<HashMapField[{uuid}]: '
                'field={field}>').format(
                    uuid=self.field_id,
                    field=self.name)


class HashMapGroup(Base, HashMapBase):
    """A grouping of hashmap calculations.

    Used to group multiple mappings or thresholds into a single calculation.
    """
    __tablename__ = 'hashmap_groups'

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True)
    group_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        nullable=False,
        unique=True)
    name = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=False,
        unique=True)
    mappings = orm.relationship(
        'HashMapMapping',
        backref=orm.backref(
            'group',
            lazy='immediate'))
    thresholds = orm.relationship(
        'HashMapThreshold',
        backref=orm.backref(
            'group',
            lazy='immediate'))

    def __repr__(self):
        return ('<HashMapGroup[{uuid}]: '
                'name={name}>').format(
                    uuid=self.group_id,
                    name=self.name)


class HashMapMapping(Base, HashMapBase):
    """A mapping between a field or service, a value and a type.

    Used to model final equation.
    """
    __tablename__ = 'hashmap_mappings'
    fk_to_resolve = {
        'service_id': 'service.service_id',
        'field_id': 'field.field_id',
        'group_id': 'group.group_id'}

    @declarative.declared_attr
    def __table_args__(cls):
        args = (
            schema.UniqueConstraint(
                'value',
                'field_id',
                name='uniq_field_mapping'),
            schema.UniqueConstraint(
                'value',
                'service_id',
                name='uniq_service_mapping'),
            HashMapBase.__table_args__,)
        return args

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True)
    mapping_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        nullable=False,
        unique=True)
    value = sqlalchemy.Column(
        sqlalchemy.String(255),
        nullable=True)
    cost = sqlalchemy.Column(
        sqlalchemy.Numeric(20, 8),
        nullable=False)
    map_type = sqlalchemy.Column(
        sqlalchemy.Enum(
            'flat',
            'rate',
            name='enum_map_type'),
        nullable=False)
    service_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_services.id',
            ondelete='CASCADE'),
        nullable=True)
    field_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_fields.id',
            ondelete='CASCADE'),
        nullable=True)
    group_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_groups.id',
            ondelete='SET NULL'),
        nullable=True)

    def __repr__(self):
        return ('<HashMapMapping[{uuid}]: '
                'type={map_type} {value}={cost}>').format(
                    uuid=self.mapping_id,
                    map_type=self.map_type,
                    value=self.value,
                    cost=self.cost)


class HashMapThreshold(Base, HashMapBase):
    """A threshold matching a service or a field with a level and a type.

    Used to model final equation.
    """
    __tablename__ = 'hashmap_thresholds'
    fk_to_resolve = {
        'service_id': 'service.service_id',
        'field_id': 'field.field_id',
        'group_id': 'group.group_id'}

    @declarative.declared_attr
    def __table_args__(cls):
        args = (
            schema.UniqueConstraint(
                'level',
                'field_id',
                name='uniq_field_threshold'),
            schema.UniqueConstraint(
                'level',
                'service_id',
                name='uniq_service_threshold'),
            HashMapBase.__table_args__,)
        return args

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True)
    threshold_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        nullable=False,
        unique=True)
    level = sqlalchemy.Column(
        sqlalchemy.Numeric(20, 8),
        nullable=True)
    cost = sqlalchemy.Column(
        sqlalchemy.Numeric(20, 8),
        nullable=False)
    map_type = sqlalchemy.Column(
        sqlalchemy.Enum(
            'flat',
            'rate',
            name='enum_hashmap_type'),
        nullable=False)
    service_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_services.id',
            ondelete='CASCADE'),
        nullable=True)
    field_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_fields.id',
            ondelete='CASCADE'),
        nullable=True)
    group_id = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey(
            'hashmap_groups.id',
            ondelete='SET NULL'),
        nullable=True)

    def __repr__(self):
        return ('<HashMapThreshold[{uuid}]: '
                'type={map_type} {level}={cost}>').format(
                    uuid=self.threshold_id,
                    map_type=self.map_type,
                    level=self.level,
                    cost=self.cost)
