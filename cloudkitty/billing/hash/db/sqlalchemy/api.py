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
from oslo.db import exception
from oslo.db.sqlalchemy import utils
import six
import sqlalchemy

from cloudkitty.billing.hash.db import api
from cloudkitty.billing.hash.db.sqlalchemy import migration
from cloudkitty.billing.hash.db.sqlalchemy import models
from cloudkitty import db
from cloudkitty.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def get_backend():
    return HashMap()


class HashMap(api.HashMap):

    def get_migration(self):
        return migration

    def get_service(self, service):
        session = db.get_session()
        try:
            q = session.query(models.HashMapService)
            res = q.filter_by(
                name=service,
            ).one()
            return res
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchService(service)

    def get_field(self, service, field):
        session = db.get_session()
        try:
            service_db = self.get_service(service)
            q = session.query(models.HashMapField)
            res = q.filter_by(
                service_id=service_db.id,
                name=field
            ).one()
            return res
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchField(service, field)

    def get_mapping(self, service, field, key):
        session = db.get_session()
        try:
            field_db = self.get_field(service, field)
            q = session.query(models.HashMapMapping)
            res = q.filter_by(
                key=key,
                field_id=field_db.id
            ).one()
            return res
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchMapping(service, field, key)

    def list_services(self):
        session = db.get_session()
        q = session.query(models.HashMapService)
        res = q.values(
            models.HashMapService.name
        )
        return res

    def list_fields(self, service):
        session = db.get_session()
        service_db = self.get_service(service)
        q = session.query(models.HashMapField)
        res = q.filter_by(
            service_id=service_db.id
        ).values(
            models.HashMapField.name
        )
        return res

    def list_mappings(self, service, field):
        session = db.get_session()
        field_db = self.get_field(service, field)
        q = session.query(models.HashMapMapping)
        res = q.filter_by(
            field_id=field_db.id
        ).values(
            models.HashMapMapping.key
        )
        return res

    def create_service(self, service):
        session = db.get_session()
        try:
            with session.begin():
                service_db = models.HashMapService(name=service)
                session.add(service_db)
                session.flush()
                # TODO(sheeprine): return object
                return service_db
        except exception.DBDuplicateEntry:
            raise api.ServiceAlreadyExists(service)

    def create_field(self, service, field):
        try:
            service_db = self.get_service(service)
        except api.NoSuchService:
            service_db = self.create_service(service)
        session = db.get_session()
        try:
            with session.begin():
                field_db = models.HashMapField(
                    service_id=service_db.id,
                    name=field)
                session.add(field_db)
                session.flush()
                # TODO(sheeprine): return object
                return field_db
        except exception.DBDuplicateEntry:
            raise api.FieldAlreadyExists(field)

    def create_mapping(self, service, field, key, value, map_type='rate'):
        try:
            field_db = self.get_field(service, field)
        except (api.NoSuchField, api.NoSuchService):
            field_db = self.create_field(service, field)
        session = db.get_session()
        try:
            with session.begin():
                field_map = models.HashMapMapping(
                    field_id=field_db.id,
                    key=key,
                    value=value,
                    map_type=map_type)
                session.add(field_map)
                # TODO(sheeprine): return object
                return field_map
        except exception.DBDuplicateEntry:
            raise api.MappingAlreadyExists(key)

    def update_mapping(self, service, field, key, **kwargs):
        field_db = self.get_field(service, field)
        session = db.get_session()
        try:
            with session.begin():
                q = session.query(models.HashMapMapping)
                field_map = q.filter_by(
                    key=key,
                    field_id=field_db.id
                ).with_lockmode('update').one()
                if kwargs:
                    for attribute, value in six.iteritems(kwargs):
                        if hasattr(field_map, attribute):
                            setattr(field_map, attribute, value)
                        else:
                            raise ValueError('No such attribute: {}'.format(
                                attribute))
                else:
                    raise ValueError('No attribute to update.')
                return field_map
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchMapping(service, field, key)

    def update_or_create_mapping(self, service, field, key, **kwargs):
        try:
            return self.create_mapping(
                service,
                field,
                key,
                **kwargs
            )
        except api.MappingAlreadyExists:
            return self.update_mapping(service, field, key, **kwargs)

    def delete_service(self, service):
        session = db.get_session()
        r = utils.model_query(
            models.HashMapService,
            session
        ).filter_by(
            name=service,
        ).delete()
        if not r:
            raise api.NoSuchService(service)

    def delete_field(self, service, field):
        session = db.get_session()
        service_db = self.get_service(service)
        r = utils.model_query(
            models.HashMapField,
            session
        ).filter_by(
            service_id=service_db.id,
            name=field,
        ).delete()
        if not r:
            raise api.NoSuchField(service, field)

    def delete_mapping(self, service, field, key):
        session = db.get_session()
        field = self.get_field(service, field)
        r = utils.model_query(
            models.HashMapMapping,
            session
        ).filter_by(
            field_id=field.id,
            key=key,
        ).delete()
        if not r:
            raise api.NoSuchMapping(service, field, key)
