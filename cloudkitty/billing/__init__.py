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

import pecan
from pecan import rest
import six
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.db import api as db_api


class BillingModuleNotConfigurable(Exception):
    def __init__(self, module):
        self.module = module
        super(BillingModuleNotConfigurable, self).__init__(
            'Module %s not configurable.' % module)


class ExtensionSummary(wtypes.Base):
    """A billing extension summary

    """

    name = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of the extension."""

    description = wtypes.text
    """Short description of the extension."""

    enabled = wtypes.wsattr(bool, default=False)
    """Extension status."""

    hot_config = wtypes.wsattr(bool, default=False, name='hot-config')
    """On-the-fly configuration support."""

    @classmethod
    def sample(cls):
        sample = cls(name='example',
                     description='Sample extension.',
                     enabled=True,
                     hot_config=False)
        return sample


@six.add_metaclass(abc.ABCMeta)
class BillingEnableController(rest.RestController):
    """REST Controller to enable or disable a billing module.

    """

    @wsme_pecan.wsexpose(bool)
    def get(self):
        """Get module status

        """
        api = db_api.get_instance()
        module_db = api.get_module_enable_state()
        return module_db.get_state(self.module_name) or False

    @wsme_pecan.wsexpose(bool, body=bool)
    def put(self, state):
        """Set module status

        :param state: State to set.
        :return: New state set for the module.
        """
        api = db_api.get_instance()
        module_db = api.get_module_enable_state()
        return module_db.set_state(self.module_name, state)


@six.add_metaclass(abc.ABCMeta)
class BillingConfigController(rest.RestController):
    """REST Controller managing internal configuration of billing modules.

    """

    def _not_configurable(self):
        try:
            raise BillingModuleNotConfigurable(self.module_name)
        except BillingModuleNotConfigurable as e:
            pecan.abort(400, str(e))

    @wsme_pecan.wsexpose()
    def get(self):
        """Get current module configuration

        """
        self._not_configurable()

    @wsme_pecan.wsexpose()
    def put(self):
        """Set current module configuration

        """
        self._not_configurable()


@six.add_metaclass(abc.ABCMeta)
class BillingController(rest.RestController):
    """REST Controller used to manage billing system.

    """

    config = BillingConfigController()
    enabled = BillingEnableController()

    def __init__(self):
        if hasattr(self, 'module_name'):
            self.config.module_name = self.module_name
            self.enabled.module_name = self.module_name

    @wsme_pecan.wsexpose(ExtensionSummary)
    def get_all(self):
        """Get extension summary.

        """
        extension_summary = ExtensionSummary(**self.get_module_info())
        return extension_summary

    @abc.abstractmethod
    def get_module_info(self):
        """Get module informations

        """


@six.add_metaclass(abc.ABCMeta)
class BillingProcessorBase(object):

    controller = BillingController

    def __init__(self):
        pass

    @abc.abstractproperty
    def enabled(self):
        """Check if the module is enabled

        :returns: bool if module is enabled
        """

    @abc.abstractmethod
    def reload_config(self):
        """Trigger configuration reload

        """

    @abc.abstractmethod
    def process(self, data):
        """Add billing informations to data

        :param data: An internal CloudKitty dictionary used to describe
                     resources.
        :type data: dict(str:?)
        """
