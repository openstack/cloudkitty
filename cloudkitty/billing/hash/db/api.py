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

from oslo.config import cfg
from oslo.db import api as db_api
import six

_BACKEND_MAPPING = {'sqlalchemy': 'cloudkitty.billing.hash.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF,
                                backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


class NoSuchService(Exception):
    """Raised when the service doesn't exist."""

    def __init__(self, service):
        super(NoSuchService, self).__init__(
            "No such service: %s" % service)
        self.service = service


class NoSuchField(Exception):
    """Raised when the field doesn't exist for the service."""

    def __init__(self, service, field):
        super(NoSuchField, self).__init__(
            "No such field for %s service: %s" % (service, field,))
        self.service = service
        self.field = field


class NoSuchMapping(Exception):
    """Raised when the mapping doesn't exist."""

    def __init__(self, service, field, key):
        super(NoSuchMapping, self).__init__(
            "No such key for %s service and %s field: %s"
            % (service, field, key,))
        self.service = service
        self.field = field
        self.key = key


class ServiceAlreadyExists(Exception):
    """Raised when the service already exists."""

    def __init__(self, service):
        super(ServiceAlreadyExists, self).__init__(
            "Service %s already exists" % service)
        self.service = service


class FieldAlreadyExists(Exception):
    """Raised when the field already exists."""

    def __init__(self, field):
        super(FieldAlreadyExists, self).__init__(
            "Field %s already exists" % field)
        self.field = field


class MappingAlreadyExists(Exception):
    """Raised when the mapping already exists."""

    def __init__(self, mapping):
        super(MappingAlreadyExists, self).__init__(
            "Mapping %s already exists" % mapping)
        self.mapping = mapping


@six.add_metaclass(abc.ABCMeta)
class HashMap(object):
    """Base class for hashmap configuration."""

    @abc.abstractmethod
    def get_migrate(self):
        """Return a migrate manager.

        """

    @abc.abstractmethod
    def get_service(self, service):
        """Return a service object.

        :param service: The service to filter on.
        """

    @abc.abstractmethod
    def get_field(self, service, field):
        """Return a field object.

        :param service: The service to filter on.
        :param field: The field to filter on.
        """

    @abc.abstractmethod
    def get_mapping(self, service, field, key):
        """Return a field object.

        :param service: The service to filter on.
        :param field: The field to filter on.
        :param key: The field to filter on.
        :param key: Value of the field to filter on.
        """

    @abc.abstractmethod
    def list_services(self):
        """Return a list of every services.

        """

    @abc.abstractmethod
    def list_fields(self, service):
        """Return a list of every fields in a service.

        :param service: The service to filter on.
        """

    @abc.abstractmethod
    def list_mappings(self, service, field):
        """Return a list of every mapping.

        :param service: The service to filter on.
        :param field: The key to filter on.
        """

    @abc.abstractmethod
    def create_service(self, service):
        """Create a new service.

        :param service:
        """

    @abc.abstractmethod
    def create_field(self, service, field):
        """Create a new field.

        :param service:
        :param field:
        """

    @abc.abstractmethod
    def create_mapping(self, service, field, key, value, map_type='rate'):
        """Create a new service/field mapping.

        :param service: Service the mapping is applying to.
        :param field: Field the mapping is applying to.
        :param key: Value of the field this mapping is applying to.
        :param value: Pricing value to apply to this mapping.
        :param map_type: The type of pricing rule.
        """

    @abc.abstractmethod
    def update_mapping(self, service, field, key, **kwargs):
        """Update a mapping.

        :param service: Service the mapping is applying to.
        :param field: Field the mapping is applying to.
        :param key: Value of the field this mapping is applying to.
        :param value: Pricing value to apply to this mapping.
        :param map_type: The type of pricing rule.
        """

    @abc.abstractmethod
    def update_or_create_mapping(self, service, field, key, **kwargs):
        """Update or create a mapping.

        :param service: Service the mapping is applying to.
        :param field: Field the mapping is applying to.
        :param key: Value of the field this mapping is applying to.
        :param value: Pricing value to apply to this mapping.
        :param map_type: The type of pricing rule.
        """

    @abc.abstractmethod
    def delete_service(self, service):
        """Delete a service recursively.

        :param service: Service to delete.
        """

    @abc.abstractmethod
    def delete_field(self, service, field):
        """Delete a field recursively.

        :param service: Service the field is applying to.
        :param field: field to delete.
        """

    @abc.abstractmethod
    def delete_mapping(self, service, field, key):
        """Delete a mapping recursively.

        :param service: Service the field is applying to.
        :param field: Field the mapping is applying to.
        :param key: key to delete.
        """
