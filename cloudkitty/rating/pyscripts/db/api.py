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
import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six

_BACKEND_MAPPING = {
    'sqlalchemy': 'cloudkitty.rating.pyscripts.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF,
                                backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


class NoSuchScript(Exception):
    """Raised when the script doesn't exist."""

    def __init__(self, name=None, uuid=None):
        super(NoSuchScript, self).__init__(
            "No such script: %s (UUID: %s)" % (name, uuid))
        self.name = name
        self.uuid = uuid


class ScriptAlreadyExists(Exception):
    """Raised when the script already exists."""

    def __init__(self, name, uuid):
        super(ScriptAlreadyExists, self).__init__(
            "Script %s already exists (UUID: %s)" % (name, uuid))
        self.name = name
        self.uuid = uuid


@six.add_metaclass(abc.ABCMeta)
class PyScripts(object):
    """Base class for pyscripts configuration."""

    @abc.abstractmethod
    def get_migration(self):
        """Return a migrate manager.

        """

    @abc.abstractmethod
    def get_script(self, name=None, uuid=None):
        """Return a script object.

        :param name: Filter on a script name.
        :param uuid: The uuid of the script to get.
        """

    @abc.abstractmethod
    def list_scripts(self):
        """Return a UUID list of every scripts available.

        """

    @abc.abstractmethod
    def create_script(self, name, data):
        """Create a new script.

        :param name: Name of the script to create.
        :param data: Content of the python script.
        """

    @abc.abstractmethod
    def update_script(self, uuid, **kwargs):
        """Update a script.

        :param uuid UUID of the script to modify.
        :param data: Script data.
        """

    @abc.abstractmethod
    def delete_script(self, name=None, uuid=None):
        """Delete a list.

        :param name: Name of the script to delete.
        :param uuid: UUID of the script to delete.
        """
