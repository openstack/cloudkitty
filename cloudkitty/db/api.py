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

_BACKEND_MAPPING = {'sqlalchemy': 'cloudkitty.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF,
                                backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class State(object):
    """Base class for state tracking."""

    @abc.abstractmethod
    def get_state(self, name):
        """Retrieve the current state.

        :param name: Name of the state
        :return float: State value
        """

    @abc.abstractmethod
    def set_state(self, name, state):
        """Store the state.

        :param name: Name of the state
        :param state: State value
        """

    @abc.abstractmethod
    def get_metadata(self, name):
        """Retrieve state metadata

        :param name: Name of the state
        :return str: Return a json dict with all metadata attached to this
        state.
        """

    @abc.abstractmethod
    def set_metadata(self, name, metadata):
        """Store the state metadata.

        :param name: Name of the state
        :param metadata: Metadata value
        """


@six.add_metaclass(abc.ABCMeta)
class ModuleInfo(object):
    """Base class for module info management."""

    @abc.abstractmethod
    def get_priority(self, name):
        """Retrieve the module priority.

        :param name: Name of the module
        :return int: Priority of the module
        """

    @abc.abstractmethod
    def set_priority(self, name, priority):
        """Set the module state.

        :param name: Name of the module
        :param priority: New priority of the module
        """

    @abc.abstractmethod
    def get_state(self, name):
        """Retrieve the module state.

        :param name: Name of the module
        :return bool: State of the module
        """

    @abc.abstractmethod
    def set_state(self, name, state):
        """Set the module state.

        :param name: Name of the module
        :param value: State of the module
        """


class NoSuchMapping(Exception):
    """Raised when the mapping doesn't exist."""

    def __init__(self, service):
        super(NoSuchMapping, self).__init__(
            "No mapping for service: %s" % service)
        self.service = service


@six.add_metaclass(abc.ABCMeta)
class ServiceToCollectorMapping(object):
    """Base class for service to collector mapping."""

    @abc.abstractmethod
    def get_mapping(self, service):
        """Get a mapping.

        :return mapping: service to collector object.
        """

    @abc.abstractmethod
    def set_mapping(self, service, collector):
        """Set a mapping.

        :param service: Service to work on.
        :param collector: Collector to prioritize.
        :return mapping: Service to Collector object.
        """

    @abc.abstractmethod
    def list_services(self, collector=None):
        """Retrieve the list of every services mapped.

        :param collector: Filter on a collector name.
        :return list(str): List of services' name.
        """
    @abc.abstractmethod
    def list_mappings(self, collector=None):
        """Retrieve the list of every mappings.

        :param collector: Filter on a collector's name.
        :return [tuple(str, str)]: List of mappings.
        """

    @abc.abstractmethod
    def delete_mapping(self, service):
        """Remove a mapping.

        """
