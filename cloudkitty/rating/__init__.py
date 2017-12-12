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

from cloudkitty.common import policy
from cloudkitty.db import api as db_api
from cloudkitty import messaging


@six.add_metaclass(abc.ABCMeta)
class RatingProcessorBase(object):
    """Provides the Cloudkitty integration code to the rating processors.

    Every rating processor should subclass this and override at least
    module_name, description.

    config_controller can be left at None to use the default one.
    """

    module_name = None
    description = None
    config_controller = None
    hot_config = False

    @property
    def module_info(self):
        return {
            'name': self.module_name,
            'description': self.description,
            'hot_config': self.hot_config,
            'enabled': self.enabled,
            'priority': self.priority}

    def __init__(self, tenant_id=None):
        self._tenant_id = tenant_id

    @property
    def enabled(self):
        """Check if the module is enabled

        :returns: bool if module is enabled
        """
        api = db_api.get_instance()
        module_db = api.get_module_info()
        return module_db.get_state(self.module_name) or False

    @property
    def priority(self):
        """Get the priority of the module.

        """
        api = db_api.get_instance()
        module_db = api.get_module_info()
        return module_db.get_priority(self.module_name)

    def set_priority(self, priority):
        """Set the priority of the module.

        :param priority: (int) The new priority, the higher the number, the
        higher the priority.
        """
        api = db_api.get_instance()
        module_db = api.get_module_info()
        self.notify_reload()
        return module_db.set_priority(self.module_name, priority)

    def set_state(self, enabled):
        """Enable or disable a module.

        :param enabled: (bool) The state to put the module in.
        :return:  bool
        """
        api = db_api.get_instance()
        module_db = api.get_module_info()
        client = messaging.get_client().prepare(namespace='rating',
                                                fanout=True)
        if enabled:
            operation = 'enable_module'
        else:
            operation = 'disable_module'
        client.cast({}, operation, name=self.module_name)
        return module_db.set_state(self.module_name, enabled)

    def quote(self, data):
        """Compute rating informations from data.

        :param data: An internal CloudKitty dictionary used to describe
                     resources.
        :type data: dict(str:?)
        """
        return self.process(data)

    def nodata(self, begin, end):
        """Handle billing processing when no data has been collected.

        :param begin: Begin of the period.
        :param end: End of the period.
        """
        pass

    @abc.abstractmethod
    def process(self, data):
        """Add rating informations to data

        :param data: An internal CloudKitty dictionary used to describe
                     resources.
        :type data: dict(str:?)
        """

    @abc.abstractmethod
    def reload_config(self):
        """Trigger configuration reload

        """

    def notify_reload(self):
        client = messaging.get_client().prepare(namespace='rating',
                                                fanout=True)
        client.cast({}, 'reload_module', name=self.module_name)


class RatingRestControllerBase(rest.RestController):
    @pecan.expose()
    def _route(self, args, request):
        try:
            policy.authorize(request.context, 'rating:module_config', {})
        except policy.PolicyNotAuthorized as e:
            pecan.abort(403, six.text_type(e))

        return super(RatingRestControllerBase, self)._route(args, request)
