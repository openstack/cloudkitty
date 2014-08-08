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

    description = wtypes.text

    enabled = wtypes.wsattr(bool, default=False)

    hot_config = wtypes.wsattr(bool, default=False, name='hot-config')


@six.add_metaclass(abc.ABCMeta)
class BillingEnableController(rest.RestController):

    @wsme_pecan.wsexpose(bool)
    def get(self):
        api = db_api.get_instance()
        module = pecan.request.path.rsplit('/', 2)[-2]
        module_db = api.get_module_enable_state()
        return module_db.get_state(module) or False

    @wsme_pecan.wsexpose(bool, body=bool)
    def put(self, state):
        api = db_api.get_instance()
        module = pecan.request.path.rsplit('/', 2)[-2]
        module_db = api.get_module_enable_state()
        return module_db.set_state(module, state)


@six.add_metaclass(abc.ABCMeta)
class BillingConfigController(rest.RestController):

    @wsme_pecan.wsexpose()
    def get(self):
        try:
            module = pecan.request.path.rsplit('/', 1)[-1]
            raise BillingModuleNotConfigurable(module)
        except BillingModuleNotConfigurable as e:
            pecan.abort(400, str(e))


@six.add_metaclass(abc.ABCMeta)
class BillingController(rest.RestController):

    config = BillingConfigController()
    enabled = BillingEnableController()

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
