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
import datetime

from oslo_db import exception
from oslo_db.sqlalchemy import utils
from oslo_utils import uuidutils
import sqlalchemy

from cloudkitty import db
from cloudkitty.rating.common.db.filters import get_filters
from cloudkitty.rating.hash.db import api
from cloudkitty.rating.hash.db.sqlalchemy import migration
from cloudkitty.rating.hash.db.sqlalchemy import models


def get_backend():
    return HashMap()


class HashMap(api.HashMap):

    def get_migration(self):
        return migration

    def get_service(self, name=None, uuid=None):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapService)
                if name:
                    q = q.filter(
                        models.HashMapService.name == name)
                elif uuid:
                    q = q.filter(
                        models.HashMapService.service_id == uuid)
                else:
                    raise api.ClientHashMapError(
                        'You must specify either name or uuid.')
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchService(name=name, uuid=uuid)

    def get_field(self, uuid=None, service_uuid=None, name=None):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapField)
                if uuid:
                    q = q.filter(
                        models.HashMapField.field_id == uuid)
                elif service_uuid and name:
                    q = q.join(
                        models.HashMapField.service)
                    q = q.filter(
                        models.HashMapService.service_id == service_uuid,
                        models.HashMapField.name == name)
                else:
                    raise api.ClientHashMapError(
                        'You must specify either a uuid'
                        ' or a service_uuid and a name.')
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchField(uuid)

    def get_group(self, uuid=None, name=None):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapGroup)
                if uuid:
                    q = q.filter(
                        models.HashMapGroup.group_id == uuid)
                if name:
                    q = q.filter(
                        models.HashMapGroup.name == name)
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchGroup(name, uuid)

    def get_mapping(self, uuid):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapMapping)
                q = q.filter(
                    models.HashMapMapping.mapping_id == uuid)
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchMapping(uuid)

    def get_mapping_by_name(self, name):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapMapping)
                q = q.filter(
                    models.HashMapMapping.deleted == sqlalchemy.null(),
                    models.HashMapMapping.name == name)
                res = q.all()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchMapping(name)

    def get_threshold(self, uuid):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapThreshold)
                q = q.filter(
                    models.HashMapThreshold.threshold_id == uuid)
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchThreshold(uuid)

    def get_group_from_mapping(self, uuid):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapGroup)
                q = q.join(
                    models.HashMapGroup.mappings)
                q = q.filter(
                    models.HashMapMapping.mapping_id == uuid)
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.MappingHasNoGroup(uuid=uuid)

    def get_group_from_threshold(self, uuid):
        with db.session_for_read() as session:
            try:
                q = session.query(models.HashMapGroup)
                q = q.join(
                    models.HashMapGroup.thresholds)
                q = q.filter(
                    models.HashMapThreshold.threshold_id == uuid)
                res = q.one()
                return res
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.ThresholdHasNoGroup(uuid=uuid)

    def list_services(self):
        with db.session_for_read() as session:
            q = session.query(models.HashMapService)
            res = q.values(
                models.HashMapService.service_id)
            return [uuid[0] for uuid in res]

    def list_fields(self, service_uuid):
        with db.session_for_read() as session:
            q = session.query(models.HashMapField)
            q = q.join(
                models.HashMapField.service)
            q = q.filter(
                models.HashMapService.service_id == service_uuid)
            res = q.values(models.HashMapField.field_id)
            return [uuid[0] for uuid in res]

    def list_groups(self):
        with db.session_for_read() as session:
            q = session.query(models.HashMapGroup)
            res = q.values(
                models.HashMapGroup.group_id)
            return [uuid[0] for uuid in res]

    def list_mappings(self,
                      service_uuid=None,
                      field_uuid=None,
                      group_uuid=None,
                      no_group=False,
                      all=False,
                      **kwargs):

        with db.session_for_read() as session:
            q = session.query(models.HashMapMapping)
            if service_uuid:
                q = q.join(
                    models.HashMapMapping.service)
                q = q.filter(
                    models.HashMapService.service_id == service_uuid)
            elif field_uuid:
                q = q.join(
                    models.HashMapMapping.field)
                q = q.filter(models.HashMapField.field_id == field_uuid)
            elif not (service_uuid or field_uuid or group_uuid) and not all:
                raise api.ClientHashMapError(
                    'You must specify either service_uuid,'
                    ' field_uuid or group_uuid.')
            if 'tenant_uuid' in kwargs:
                q = q.filter(
                    models.HashMapMapping.tenant_id == kwargs.pop(
                        'tenant_uuid'))
            if group_uuid:
                q = q.join(
                    models.HashMapMapping.group)
                q = q.filter(models.HashMapGroup.group_id == group_uuid)
            elif no_group:
                q = q.filter(models.HashMapMapping.group_id == None)  # noqa

            q = get_filters(q, models.HashMapMapping, **kwargs)
            res = q.values(
                models.HashMapMapping.mapping_id)
            return [uuid[0] for uuid in res]

    def list_thresholds(self,
                        service_uuid=None,
                        field_uuid=None,
                        group_uuid=None,
                        no_group=False,
                        **kwargs):

        with db.session_for_read() as session:
            q = session.query(models.HashMapThreshold)
            if service_uuid:
                q = q.join(
                    models.HashMapThreshold.service)
                q = q.filter(
                    models.HashMapService.service_id == service_uuid)
            elif field_uuid:
                q = q.join(
                    models.HashMapThreshold.field)
                q = q.filter(models.HashMapField.field_id == field_uuid)
            elif not service_uuid and not field_uuid and not group_uuid:
                raise api.ClientHashMapError(
                    'You must specify either service_uuid,'
                    ' field_uuid or group_uuid.')
            if 'tenant_uuid' in kwargs:
                q = q.filter(
                    models.HashMapThreshold.tenant_id == kwargs.get(
                        'tenant_uuid'))
            if group_uuid:
                q = q.join(
                    models.HashMapThreshold.group)
                q = q.filter(models.HashMapGroup.group_id == group_uuid)
            elif no_group:
                q = q.filter(models.HashMapThreshold.group_id == None)  # noqa
            res = q.values(
                models.HashMapThreshold.threshold_id)
            return [uuid[0] for uuid in res]

    def create_service(self, name):
        try:
            with db.session_for_write() as session:
                service_db = models.HashMapService(name=name)
                service_db.service_id = uuidutils.generate_uuid()
                session.add(service_db)
            return service_db
        except exception.DBDuplicateEntry:
            service_db = self.get_service(name=name)
            raise api.ServiceAlreadyExists(
                service_db.name,
                service_db.service_id)

    def create_field(self, service_uuid, name):
        service_db = self.get_service(uuid=service_uuid)
        try:
            with db.session_for_write() as session:
                field_db = models.HashMapField(
                    service_id=service_db.id,
                    name=name,
                    field_id=uuidutils.generate_uuid())
                session.add(field_db)
            # FIXME(sheeprine): backref are not populated as they used to be.
            #                   Querying the item again to get backref.
            field_db = self.get_field(service_uuid=service_uuid, name=name)
        except exception.DBDuplicateEntry:
            field_db = self.get_field(service_uuid=service_uuid, name=name)
            raise api.FieldAlreadyExists(field_db.name, field_db.field_id)
        else:
            return field_db

    def create_group(self, name):
        try:
            with db.session_for_write() as session:
                group_db = models.HashMapGroup(
                    name=name,
                    group_id=uuidutils.generate_uuid())
                session.add(group_db)
            return group_db
        except exception.DBDuplicateEntry:
            group_db = self.get_group(name=name)
            raise api.GroupAlreadyExists(name, group_db.group_id)

    def create_mapping(self,
                       cost,
                       map_type='rate',
                       value=None,
                       service_id=None,
                       field_id=None,
                       group_id=None,
                       tenant_id=None,
                       start=None,
                       end=None,
                       name=None,
                       description=None,
                       created_by=None):
        if not name:
            name = uuidutils.generate_uuid(False)
        if field_id and service_id:
            raise api.ClientHashMapError('You can only specify one parent.')
        elif not service_id and not field_id:
            raise api.ClientHashMapError('You must specify one parent.')
        elif value and service_id:
            raise api.ClientHashMapError(
                'You can\'t specify a value'
                ' and a service_id.')
        elif not value and field_id:
            raise api.ClientHashMapError(
                'You must specify a value'
                ' for a field mapping.')

        created_at = datetime.datetime.now()
        if not start:
            start = created_at

        field_fk = None
        if field_id:
            field_db = self.get_field(uuid=field_id)
            field_fk = field_db.id
        service_fk = None
        if service_id:
            service_db = self.get_service(uuid=service_id)
            service_fk = service_db.id
        group_fk = None
        if group_id:
            group_db = self.get_group(uuid=group_id)
            group_fk = group_db.id
        try:
            with db.session_for_write() as session:
                map_model = models.HashMapMapping
                q = session.query(map_model)
                or_ = sqlalchemy.or_
                and_ = sqlalchemy.and_
                null_ = sqlalchemy.null()
                filter_name = None
                filter_value = None
                if field_fk:
                    filter_name = map_model.field_id
                    filter_value = field_fk
                if service_fk:
                    filter_name = map_model.service_id
                    filter_value = service_fk

                q = q.filter(
                    map_model.deleted == null_)

                if end:
                    date_filter = and_(
                        map_model.start < end,
                        or_(
                            map_model.end >= start,
                            map_model.end == null_
                        )
                    )
                else:
                    date_filter = or_(
                        map_model.start > start,
                        map_model.end == null_
                    )

                if filter_name:
                    name_filter = or_(
                        map_model.name == name,
                        sqlalchemy.and_(
                            date_filter,
                            and_(
                                map_model.value == value,
                                map_model.tenant_id == tenant_id,
                                filter_name == filter_value,
                                map_model.group_id == group_fk
                            )
                        )
                    )
                else:
                    name_filter = or_(
                        map_model.name == name,
                        date_filter
                    )

                q = q.filter(name_filter)
                mapping_db = q.with_for_update().all()
                if mapping_db:
                    if field_id:
                        puuid = field_id
                        ptype = 'field'
                    else:
                        puuid = service_id
                        ptype = 'service'
                    raise api.MappingAlreadyExists(
                        value,
                        puuid,
                        ptype,
                        tenant_id=tenant_id)

                field_map = map_model(
                    mapping_id=uuidutils.generate_uuid(),
                    value=value,
                    cost=cost,
                    field_id=field_fk,
                    service_id=service_fk,
                    map_type=map_type,
                    tenant_id=tenant_id,
                    created_at=created_at,
                    start=start,
                    end=end,
                    name=name,
                    description=description,
                    deleted=None,
                    created_by=created_by,
                    updated_by=None,
                    deleted_by=None
                )
                if group_fk:
                    field_map.group_id = group_fk
                session.add(field_map)
        except exception.DBDuplicateEntry:
            if field_id:
                puuid = field_id
                ptype = 'field'
            else:
                puuid = service_id
                ptype = 'service'
            raise api.MappingAlreadyExists(
                value,
                puuid,
                ptype,
                tenant_id=tenant_id)
        except exception.DBError:
            raise api.NoSuchType(map_type)
        # FIXME(sheeprine): backref are not populated as they used to be.
        #                   Querying the item again to get backref.
        field_map = self.get_mapping(field_map.mapping_id)
        return field_map

    def create_threshold(self,
                         level,
                         cost,
                         map_type='rate',
                         service_id=None,
                         field_id=None,
                         group_id=None,
                         tenant_id=None):
        if field_id and service_id:
            raise api.ClientHashMapError('You can only specify one parent.')
        elif not service_id and not field_id:
            raise api.ClientHashMapError('You must specify one parent.')
        field_fk = None
        if field_id:
            field_db = self.get_field(uuid=field_id)
            field_fk = field_db.id
        service_fk = None
        if service_id:
            service_db = self.get_service(uuid=service_id)
            service_fk = service_db.id
        group_fk = None
        if group_id:
            group_db = self.get_group(uuid=group_id)
            group_fk = group_db.id
        try:
            with db.session_for_write() as session:
                threshold_db = models.HashMapThreshold(
                    threshold_id=uuidutils.generate_uuid(),
                    level=level,
                    cost=cost,
                    field_id=field_fk,
                    service_id=service_fk,
                    map_type=map_type,
                    tenant_id=tenant_id)
                if group_fk:
                    threshold_db.group_id = group_fk
                session.add(threshold_db)
        except exception.DBDuplicateEntry:
            if field_id:
                puuid = field_id
                ptype = 'field'
            else:
                puuid = service_id
                ptype = 'service'
            raise api.ThresholdAlreadyExists(level, puuid, ptype)
        except exception.DBError:
            raise api.NoSuchType(map_type)
        # FIXME(sheeprine): backref are not populated as they used to be.
        #                   Querying the item again to get backref.
        threshold_db = self.get_threshold(threshold_db.threshold_id)
        return threshold_db

    def update_mapping(self, uuid, **kwargs):
        try:
            with db.session_for_write() as session:
                q = session.query(models.HashMapMapping)
                q = q.filter(
                    models.HashMapMapping.mapping_id == uuid,
                    models.HashMapMapping.deleted == sqlalchemy.null())
                mapping_db = q.with_for_update().one()
                if kwargs:
                    # NOTE(sheeprine): We want to check that value is not set
                    # to a None value.
                    if mapping_db.field_id and not kwargs.get('value', 'GOOD'):
                        raise api.ClientHashMapError(
                            'You must specify a value'
                            ' for a field mapping.')
                    # Resolve FK
                    if 'group_id' in kwargs:
                        group_id = kwargs.pop('group_id')
                        if group_id:
                            group_db = self.get_group(group_id)
                            mapping_db.group_id = group_db.id
                    # Service and Field shouldn't be updated
                    excluded_cols = ['mapping_id', 'service_id', 'field_id']
                    for col in excluded_cols:
                        if col in kwargs:
                            kwargs.pop(col)
                    for attribute, value in kwargs.items():
                        if hasattr(mapping_db, attribute):
                            setattr(mapping_db, attribute, value)
                        else:
                            raise api.ClientHashMapError(
                                'No such attribute: {}'.format(
                                    attribute))
                else:
                    raise api.ClientHashMapError('No attribute to update.')
                return mapping_db
        except exception.DBDuplicateEntry:
            puuid = uuid
            ptype = 'Mapping_id'
            raise api.MappingAlreadyExists(
                value,
                puuid,
                ptype,
                tenant_id=kwargs.get('tenant_id'))
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchMapping(uuid)

    def update_threshold(self, uuid, **kwargs):
        try:
            with db.session_for_write() as session:
                q = session.query(models.HashMapThreshold)
                q = q.filter(
                    models.HashMapThreshold.threshold_id == uuid)
                threshold_db = q.with_for_update().one()
                if kwargs:
                    # Resolve FK
                    if 'group_id' in kwargs:
                        group_id = kwargs.pop('group_id')
                        if group_id:
                            group_db = self.get_group(group_id)
                            threshold_db.group_id = group_db.id
                    # Service and Field shouldn't be updated
                    excluded_cols = ['threshold_id', 'service_id', 'field_id']
                    for col in excluded_cols:
                        if col in kwargs:
                            kwargs.pop(col)
                    for attribute, value in kwargs.items():
                        if hasattr(threshold_db, attribute):
                            setattr(threshold_db, attribute, value)
                        else:
                            raise api.ClientHashMapError(
                                'No such attribute: {}'.format(
                                    attribute))
                else:
                    raise api.ClientHashMapError('No attribute to update.')
                return threshold_db
        except exception.DBDuplicateEntry:
            puuid = uuid
            ptype = 'Threshold_id'
            raise api.ThresholdAlreadyExists(
                value,
                puuid,
                ptype,
                tenant_id=kwargs.get('tenant_id'))
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchThreshold(uuid)

    def delete_service(self, name=None, uuid=None):
        with db.session_for_write() as session:
            q = utils.model_query(
                models.HashMapService,
                session)
            if name:
                q = q.filter(models.HashMapService.name == name)
            elif uuid:
                q = q.filter(models.HashMapService.service_id == uuid)
            else:
                raise api.ClientHashMapError(
                    'You must specify either name or uuid.')
            r = q.delete()
            if not r:
                raise api.NoSuchService(name, uuid)

    def delete_field(self, uuid):
        with db.session_for_write() as session:
            q = utils.model_query(
                models.HashMapField,
                session)
            q = q.filter(models.HashMapField.field_id == uuid)
            r = q.delete()
            if not r:
                raise api.NoSuchField(uuid)

    def delete_group(self, uuid, recurse=True):
        with db.session_for_write() as session:
            q = utils.model_query(
                models.HashMapGroup,
                session)
            q = q.filter(models.HashMapGroup.group_id == uuid)
            try:
                r = q.with_for_update().one()
            except sqlalchemy.orm.exc.NoResultFound:
                raise api.NoSuchGroup(uuid=uuid)
            if recurse:
                for mapping in r.mappings:
                    session.delete(mapping)
                for threshold in r.thresholds:
                    session.delete(threshold)
            q.delete()

    def delete_mapping(self, uuid, deleted_by=None):
        try:
            with db.session_for_write() as session:
                q = session.query(models.HashMapMapping)
                q = q.filter(
                    models.HashMapMapping.mapping_id == uuid,
                    models.HashMapMapping.deleted == sqlalchemy.null())
                mapping_db = q.with_for_update().one()
                mapping_db.deleted_by = deleted_by
                mapping_db.deleted = datetime.datetime.now()
        except sqlalchemy.orm.exc.NoResultFound:
            raise api.NoSuchMapping(uuid)

    def delete_threshold(self, uuid):
        with db.session_for_write() as session:
            q = utils.model_query(
                models.HashMapThreshold,
                session)
            q = q.filter(models.HashMapThreshold.threshold_id == uuid)
            r = q.delete()
            if not r:
                raise api.NoSuchThreshold(uuid)
