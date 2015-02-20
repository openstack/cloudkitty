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
import datetime

from oslo.config import cfg
import pecan
from pecan import rest
from stevedore import extension
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.controllers import types as cktypes
from cloudkitty import config  # noqa
from cloudkitty.db import api as db_api
from cloudkitty.openstack.common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CLOUDKITTY_SERVICES = wtypes.Enum(wtypes.text,
                                  *CONF.collect.services)


class ResourceDescriptor(wtypes.Base):
    """Type describing a resource in CloudKitty.

    """

    service = CLOUDKITTY_SERVICES
    """Name of the service."""

    # FIXME(sheeprine): values should be dynamic
    # Testing with ironic dynamic type
    desc = {wtypes.text: cktypes.MultiType(wtypes.text, int, float, dict)}
    """Description of the resources parameters."""

    volume = int
    """Number of resources."""

    def to_json(self):
        res_dict = {}
        res_dict[self.service] = [{'desc': self.desc,
                                   'vol': {'qty': self.volume,
                                           'unit': 'undef'}
                                   }]
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(service='compute',
                     desc={
                         'image_id': 'a41fba37-2429-4f15-aa00-b5bc4bf557bf'
                     },
                     volume=1)
        return sample


class ServiceToCollectorMapping(wtypes.Base):
    """Type describing a service to collector mapping.

    """

    service = wtypes.text
    """Name of the service."""

    collector = wtypes.text
    """Name of the collector."""

    def to_json(self):
        res_dict = {}
        res_dict[self.service] = self.collector
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(service='compute',
                     collector='ceilometer')
        return sample


class MappingController(rest.RestController):
    """REST Controller managing service to collector mapping.

    """

    def __init__(self):
        self._db = db_api.get_instance().get_service_to_collector_mapping()

    @wsme_pecan.wsexpose([wtypes.text])
    def get_all(self):
        """Return the list of every services mapped.

        :return: List of every services mapped.
        """
        return [mapping.service for mapping in self._db.list_services()]

    @wsme_pecan.wsexpose(ServiceToCollectorMapping, wtypes.text)
    def get_one(self, service):
        """Return a service to collector mapping.

        :param service: Name of the service to filter on.
        """
        try:
            return self._db.get_mapping(service)
        except db_api.NoSuchMapping as e:
            pecan.abort(400, str(e))
        pecan.response.status = 200

    @wsme_pecan.wsexpose(ServiceToCollectorMapping,
                         wtypes.text,
                         body=wtypes.text)
    def post(self, service, collector):
        """Create or modify a mapping.

        :param service: Name of the service to map a collector to.
        :param collector: Name of the collector.
        """
        return self._db.set_mapping(service, collector)

    @wsme_pecan.wsexpose(None, body=wtypes.text)
    def delete(self, service):
        """Delete a mapping.

        :param service: Name of the service to suppress the mapping from.
        """
        try:
            self._db.delete_mapping(service)
        except db_api.NoSuchMapping as e:
            pecan.abort(400, str(e))
        pecan.response.status = 204


class CollectorController(rest.RestController):
    """REST Controller managing collector modules.

    """

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
        return self._db.get_state('collector_{}'.format(collector))

    @wsme_pecan.wsexpose(bool, wtypes.text, body=bool)
    def post_state(self, collector, state):
        """Set the enable state of a collector.

        :param collector: Name of the collector.
        :param state: New state for the collector.
        :return: State of the collector.
        """
        return self._db.set_state('collector_{}'.format(collector), state)


class ModulesController(rest.RestController):
    """REST Controller managing billing modules.

    """

    def __init__(self):
        self.extensions = extension.ExtensionManager(
            'cloudkitty.billing.processors',
            # FIXME(sheeprine): don't want to load it here as we just need the
            # controller
            invoke_on_load=True
        )
        self.expose_modules()

    def expose_modules(self):
        """Load billing modules to expose API controllers.

        """
        for ext in self.extensions:
            # FIXME(sheeprine): we should notify two modules with same name
            if not hasattr(self, ext.name):
                setattr(self, ext.name, ext.obj.controller())

    @wsme_pecan.wsexpose([wtypes.text])
    def get(self):
        """Return the list of loaded modules.

        :return: Name of every loaded modules.
        """
        return [ext for ext in self.extensions.names()]


class BillingController(rest.RestController):

    _custom_actions = {
        'quote': ['POST'],
    }

    modules = ModulesController()

    @wsme_pecan.wsexpose(float, body=[ResourceDescriptor])
    def quote(self, res_data):
        """Get an instant quote based on multiple resource descriptions.

        :param res_data: List of resource descriptions.
        :return: Total price for these descriptions.
        """
        client = pecan.request.rpc_client.prepare(namespace='billing')
        res_dict = {}
        for res in res_data:
            if res.service not in res_dict:
                res_dict[res.service] = []
            json_data = res.to_json()
            res_dict[res.service].extend(json_data[res.service])

        res = client.call({}, 'quote', res_data=[{'usage': res_dict}])
        return res


class ReportController(rest.RestController):
    """REST Controller managing the reporting.

    """

    _custom_actions = {
        'total': ['GET'],
        'tenants': ['GET']
    }

    @wsme_pecan.wsexpose([wtypes.text],
                         datetime.datetime,
                         datetime.datetime)
    def tenants(self, begin=None, end=None):
        """Return the list of rated tenants.

        """
        storage = pecan.request.storage_backend
        tenants = storage.get_tenants(begin, end)
        return tenants

    @wsme_pecan.wsexpose(float,
                         datetime.datetime,
                         datetime.datetime,
                         wtypes.text)
    def total(self, begin=None, end=None, tenant_id=None):
        """Return the amount to pay for a given period.

        """
        storage = pecan.request.storage_backend
        # FIXME(sheeprine): We should filter on user id.
        # Use keystone token information by default but make it overridable and
        # enforce it by policy engine
        total = storage.get_total(begin, end, tenant_id)
        return total


class V1Controller(rest.RestController):
    """API version 1 controller.

    """

    collector = CollectorController()
    billing = BillingController()
    report = ReportController()
