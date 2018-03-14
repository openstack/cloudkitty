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
from oslo_log import log as logging
import pecan
from pecan import rest
import six
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.v1.datamodels import collector as collector_models
from cloudkitty.common import policy
from cloudkitty.db import api as db_api

LOG = logging.getLogger(__name__)


class MappingController(rest.RestController):
    """REST Controller managing service to collector mappings."""

    def __init__(self):
        self._db = db_api.get_instance().get_service_to_collector_mapping()

    @wsme_pecan.wsexpose(collector_models.ServiceToCollectorMapping,
                         wtypes.text)
    def get_one(self, service):
        """Return a service to collector mapping.

        :param service: Name of the service to filter on.
        """
        LOG.warning("Collector mappings are deprecated and shouldn't be used.")
        policy.authorize(pecan.request.context, 'collector:get_mapping', {})
        try:
            mapping = self._db.get_mapping(service)
            return collector_models.ServiceToCollectorMapping(
                **mapping.as_dict())
        except db_api.NoSuchMapping as e:
            pecan.abort(404, six.text_type(e))

    @wsme_pecan.wsexpose(collector_models.ServiceToCollectorMappingCollection,
                         wtypes.text)
    def get_all(self, collector=None):
        """Return the list of every services mapped to a collector.

        :param collector: Filter on the collector name.
        :return: Service to collector mappings collection.
        """
        LOG.warning("Collector mappings are deprecated and shouldn't be used.")
        policy.authorize(pecan.request.context, 'collector:list_mappings', {})
        mappings = [collector_models.ServiceToCollectorMapping(
            **mapping.as_dict())
            for mapping in self._db.list_mappings(collector)]
        return collector_models.ServiceToCollectorMappingCollection(
            mappings=mappings)

    @wsme_pecan.wsexpose(collector_models.ServiceToCollectorMapping,
                         wtypes.text,
                         wtypes.text)
    def post(self, collector, service):
        """Create a service to collector mapping.

        :param collector: Name of the collector to apply mapping on.
        :param service: Name of the service to apply mapping on.
        """
        LOG.warning("Collector mappings are deprecated and shouldn't be used.")
        policy.authorize(pecan.request.context, 'collector:manage_mapping', {})
        new_mapping = self._db.set_mapping(service, collector)
        return collector_models.ServiceToCollectorMapping(
            service=new_mapping.service,
            collector=new_mapping.collector)

    @wsme_pecan.wsexpose(None,
                         wtypes.text,
                         status_code=204)
    def delete(self, service):
        """Delete a service to collector mapping.

        :param service: Name of the service to filter on.
        """
        LOG.warning("Collector mappings are deprecated and shouldn't be used.")
        policy.authorize(pecan.request.context, 'collector:manage_mapping', {})
        try:
            self._db.delete_mapping(service)
        except db_api.NoSuchMapping as e:
            pecan.abort(404, six.text_type(e))


class CollectorStateController(rest.RestController):
    """REST Controller managing collector states."""

    def __init__(self):
        self._db = db_api.get_instance().get_module_info()

    @wsme_pecan.wsexpose(collector_models.CollectorInfos, wtypes.text)
    def get(self, name):
        """Query the enable state of a collector.

        :param name: Name of the collector.
        :return: State of the collector.
        """
        policy.authorize(pecan.request.context, 'collector:get_state', {})
        enabled = self._db.get_state('collector_{}'.format(name))
        collector = collector_models.CollectorInfos(name=name,
                                                    enabled=enabled)
        return collector

    @wsme_pecan.wsexpose(collector_models.CollectorInfos,
                         wtypes.text,
                         body=collector_models.CollectorInfos)
    def put(self, name, infos):
        """Set the enable state of a collector.

        :param name: Name of the collector.
        :param infos: New state informations of the collector.
        :return: State of the collector.
        """
        policy.authorize(pecan.request.context, 'collector:update_state', {})
        enabled = self._db.set_state('collector_{}'.format(name),
                                     infos.enabled)
        collector = collector_models.CollectorInfos(name=name,
                                                    enabled=enabled)
        return collector


class CollectorController(rest.RestController):
    """REST Controller managing collector modules."""

    mappings = MappingController()
    states = CollectorStateController()

    # FIXME(sheeprine): Stub function used to pass requests to subcontrollers
    @wsme_pecan.wsexpose(None)
    def get(self):
        "Unused function, hack to let pecan route requests to subcontrollers."
        return
