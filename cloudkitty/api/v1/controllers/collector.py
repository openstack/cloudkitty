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
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1.datamodels import collector as collector_models
from cloudkitty.common import policy
from cloudkitty.db import api as db_api


class MappingController(rest.RestController):
    """REST Controller managing service to collector mappings."""

    def __init__(self):
        self._db = db_api.get_instance().get_service_to_collector_mapping()

    @wsme_pecan.wsexpose([wtypes.text])
    def get_all(self):
        """Return the list of every services mapped.

        :return: List of every services mapped.
        """
        policy.enforce(pecan.request.context, 'collector:list_mappings', {})
        return [mapping.service for mapping in self._db.list_services()]

    @wsme_pecan.wsexpose(collector_models.ServiceToCollectorMapping,
                         wtypes.text)
    def get_one(self, service):
        """Return a service to collector mapping.

        :param service: Name of the service to filter on.
        """
        policy.enforce(pecan.request.context, 'collector:get_mapping', {})
        try:
            return self._db.get_mapping(service)
        except db_api.NoSuchMapping as e:
            pecan.abort(400, str(e))


class CollectorController(rest.RestController):
    """REST Controller managing collector modules."""

    mapping = MappingController()

    _custom_actions = {
        'state': ['GET', 'POST']
    }

    def __init__(self):
        self._db = db_api.get_instance().get_module_enable_state()

    @wsme_pecan.wsexpose(bool, wtypes.text)
    def state(self, collector):
        """Query the enable state of a collector.

        :param collector: Name of the collector.
        :return: State of the collector.
        """
        policy.enforce(pecan.request.context, 'collector:get_state', {})
        return self._db.get_state('collector_{}'.format(collector))

    @wsme_pecan.wsexpose(bool, wtypes.text, body=bool)
    def post_state(self, collector, state):
        """Set the enable state of a collector.

        :param collector: Name of the collector.
        :param state: New state for the collector.
        :return: State of the collector.
        """
        policy.enforce(pecan.request.context, 'collector:update_state', {})
        return self._db.set_state('collector_{}'.format(collector), state)
