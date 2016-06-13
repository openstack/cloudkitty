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
import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six

_BACKEND_MAPPING = {'sqlalchemy': 'cloudkitty.rating.hash.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF,
                                backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


class BaseHashMapError(Exception):
    """Base class for HashMap errors."""


class ClientHashMapError(BaseHashMapError):
    """Base class for client side errors."""


class NoSuchService(ClientHashMapError):
    """Raised when the service doesn't exist."""

    def __init__(self, name=None, uuid=None):
        super(NoSuchService, self).__init__(
            "No such service: %s (UUID: %s)" % (name, uuid))
        self.name = name
        self.uuid = uuid


class NoSuchField(ClientHashMapError):
    """Raised when the field doesn't exist for the service."""

    def __init__(self, uuid):
        super(NoSuchField, self).__init__(
            "No such field: %s" % uuid)
        self.uuid = uuid


class NoSuchGroup(ClientHashMapError):
    """Raised when the group doesn't exist."""

    def __init__(self, name=None, uuid=None):
        super(NoSuchGroup, self).__init__(
            "No such group: %s (UUID: %s)" % (name, uuid))
        self.name = name
        self.uuid = uuid


class NoSuchMapping(ClientHashMapError):
    """Raised when the mapping doesn't exist."""

    def __init__(self, uuid):
        msg = ("No such mapping: %s" % uuid)
        super(NoSuchMapping, self).__init__(msg)
        self.uuid = uuid


class NoSuchThreshold(ClientHashMapError):
    """Raised when the threshold doesn't exist."""

    def __init__(self, uuid):
        msg = ("No such threshold: %s" % uuid)
        super(NoSuchThreshold, self).__init__(msg)
        self.uuid = uuid


class NoSuchType(ClientHashMapError):
    """Raised when a mapping type is not handled."""

    def __init__(self, map_type):
        msg = ("No mapping type: %s"
               % (map_type))
        super(NoSuchType, self).__init__(msg)
        self.map_type = map_type


class ServiceAlreadyExists(ClientHashMapError):
    """Raised when the service already exists."""

    def __init__(self, name, uuid):
        super(ServiceAlreadyExists, self).__init__(
            "Service %s already exists (UUID: %s)" % (name, uuid))
        self.name = name
        self.uuid = uuid


class FieldAlreadyExists(ClientHashMapError):
    """Raised when the field already exists."""

    def __init__(self, field, uuid):
        super(FieldAlreadyExists, self).__init__(
            "Field %s already exists (UUID: %s)" % (field, uuid))
        self.field = field
        self.uuid = uuid


class GroupAlreadyExists(ClientHashMapError):
    """Raised when the group already exists."""

    def __init__(self, name, uuid):
        super(GroupAlreadyExists, self).__init__(
            "Group %s already exists (UUID: %s)" % (name, uuid))
        self.name = name
        self.uuid = uuid


class MappingAlreadyExists(ClientHashMapError):
    """Raised when the mapping already exists."""

    def __init__(self,
                 mapping,
                 parent_id=None,
                 parent_type=None,
                 uuid=None,
                 tenant_id=None):
        # TODO(sheeprine): UUID is deprecated
        parent_id = parent_id if parent_id else uuid
        super(MappingAlreadyExists, self).__init__(
            "Mapping '%s' already exists for %s '%s', tenant: '%s'"
            % (mapping, parent_type, parent_id, tenant_id))
        self.mapping = mapping
        self.uuid = parent_id
        self.parent_id = parent_id
        self.parent_type = parent_type
        self.tenant_id = tenant_id


class ThresholdAlreadyExists(ClientHashMapError):
    """Raised when the threshold already exists."""

    def __init__(self,
                 threshold,
                 parent_id=None,
                 parent_type=None,
                 uuid=None,
                 tenant_id=None):
        # TODO(sheeprine): UUID is deprecated
        parent_id = parent_id if parent_id else uuid
        super(ThresholdAlreadyExists, self).__init__(
            "Threshold '%s' already exists for %s '%s', tenant: '%s'"
            % (threshold, parent_type, parent_id, tenant_id))
        self.threshold = threshold
        self.uuid = parent_id
        self.parent_id = parent_id
        self.parent_type = parent_type
        self.tenant_id = tenant_id


class MappingHasNoGroup(ClientHashMapError):
    """Raised when the mapping is not attached to a group."""

    def __init__(self, uuid):
        super(MappingHasNoGroup, self).__init__(
            "Mapping has no group (UUID: %s)" % uuid)
        self.uuid = uuid


class ThresholdHasNoGroup(ClientHashMapError):
    """Raised when the threshold is not attached to a group."""

    def __init__(self, uuid):
        super(ThresholdHasNoGroup, self).__init__(
            "Threshold has no group (UUID: %s)" % uuid)
        self.uuid = uuid


@six.add_metaclass(abc.ABCMeta)
class HashMap(object):
    """Base class for hashmap configuration."""

    @abc.abstractmethod
    def get_migration(self):
        """Return a migrate manager.

        """

    @abc.abstractmethod
    def get_service(self, name=None, uuid=None):
        """Return a service object.

        :param name: Filter on a service name.
        :param uuid: The uuid of the service to get.
        """

    @abc.abstractmethod
    def get_field(self, uuid=None, service_uuid=None, name=None):
        """Return a field object.

        :param uuid: UUID of the field to get.
        :param service_uuid: UUID of the service to filter on. (Used with name)
        :param name: Name of the field to filter on. (Used with service_uuid)
        """

    @abc.abstractmethod
    def get_group(self, uuid=None, name=None):
        """Return a group object.

        :param uuid: UUID of the group to get.
        :param name: Name of the group to get.
        """

    @abc.abstractmethod
    def get_mapping(self, uuid):
        """Return a mapping object.

        :param uuid: UUID of the mapping to get.
        """

    @abc.abstractmethod
    def get_threshold(self, uuid):
        """Return a threshold object.

        :param uuid: UUID of the threshold to get.
        """

    @abc.abstractmethod
    def list_services(self):
        """Return an UUID list of every service.

        """

    @abc.abstractmethod
    def list_fields(self, service_uuid):
        """Return an UUID list of every field in a service.

        :param service_uuid: The service UUID to filter on.
        """

    @abc.abstractmethod
    def list_groups(self):
        """Return an UUID list of every group.

        """

    @abc.abstractmethod
    def list_mappings(self,
                      service_uuid=None,
                      field_uuid=None,
                      group_uuid=None,
                      no_group=False,
                      **kwargs):
        """Return an UUID list of every mapping.

        :param service_uuid: The service to filter on.
        :param field_uuid: The field to filter on.
        :param group_uuid: The group to filter on.
        :param no_group: Filter on mappings without a group.
        :param tenant_uuid: The tenant to filter on.

        :return list(str): List of mappings' UUID.
        """

    @abc.abstractmethod
    def list_thresholds(self,
                        service_uuid=None,
                        field_uuid=None,
                        group_uuid=None,
                        no_group=False,
                        **kwargs):
        """Return an UUID list of every threshold.

        :param service_uuid: The service to filter on.
        :param field_uuid: The field to filter on.
        :param group_uuid: The group to filter on.
        :param no_group: Filter on thresholds without a group.
        :param tenant_uuid: The tenant to filter on.

        :return list(str): List of thresholds' UUID.
        """

    @abc.abstractmethod
    def create_service(self, name):
        """Create a new service.

        :param name: Name of the service to create.
        """

    @abc.abstractmethod
    def create_field(self, service_uuid, name):
        """Create a new field.

        :param service_uuid: UUID of the parent service.
        :param name: Name of the field.
        """

    @abc.abstractmethod
    def create_group(self, name):
        """Create a new group.

        :param name: The name of the group.
        """

    @abc.abstractmethod
    def create_mapping(self,
                       cost,
                       map_type='rate',
                       value=None,
                       service_id=None,
                       field_id=None,
                       group_id=None,
                       tenant_id=None):
        """Create a new service/field mapping.

        :param cost: Rating value to apply to this mapping.
        :param map_type: The type of rating rule.
        :param value: Value of the field this mapping is applying to.
        :param service_id: Service the mapping is applying to.
        :param field_id: Field the mapping is applying to.
        :param group_id: The group of calculations to apply.
        :param tenant_id: The tenant to apply calculations to.
        """

    @abc.abstractmethod
    def create_threshold(self,
                         cost,
                         map_type='rate',
                         level=None,
                         service_id=None,
                         field_id=None,
                         group_id=None,
                         tenant_id=None):
        """Create a new service/field threshold.

        :param cost: Rating value to apply to this threshold.
        :param map_type: The type of rating rule.
        :param level: Level of the field this threshold is applying to.
        :param service_id: Service the threshold is applying to.
        :param field_id: Field the threshold is applying to.
        :param group_id: The group of calculations to apply.
        :param tenant_id: The tenant to apply calculations to.
        """

    @abc.abstractmethod
    def update_mapping(self, uuid, **kwargs):
        """Update a mapping.

        :param uuid UUID of the mapping to modify.
        :param cost: Rating value to apply to this mapping.
        :param map_type: The type of rating rule.
        :param value: Value of the field this mapping is applying to.
        :param group_id: The group of calculations to apply.
        """

    @abc.abstractmethod
    def update_threshold(self, uuid, **kwargs):
        """Update a mapping.

        :param uuid UUID of the threshold to modify.
        :param cost: Rating value to apply to this threshold.
        :param map_type: The type of rating rule.
        :param level: Level of the field this threshold is applying to.
        :param group_id: The group of calculations to apply.
        """

    @abc.abstractmethod
    def delete_service(self, name=None, uuid=None):
        """Delete a service recursively.

        :param name: Name of the service to delete.
        :param uuid: UUID of the service to delete.
        """

    @abc.abstractmethod
    def delete_field(self, uuid):
        """Delete a field recursively.

        :param uuid UUID of the field to delete.
        """

    def delete_group(self, uuid, recurse=True):
        """Delete a group and all mappings recursively.

        :param uuid: UUID of the group to delete.
        :param recurse: Delete attached mappings recursively.
        """

    @abc.abstractmethod
    def delete_mapping(self, uuid):
        """Delete a mapping

        :param uuid: UUID of the mapping to delete.
        """
    @abc.abstractmethod
    def delete_threshold(self, uuid):
        """Delete a threshold

        :param uuid: UUID of the threshold to delete.
        """
