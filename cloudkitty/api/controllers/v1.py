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
from oslo.config import cfg
from pecan import rest
from stevedore import extension
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.api.controllers import types as cktypes
from cloudkitty import config  # noqa
from cloudkitty.openstack.common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

CLOUDKITTY_SERVICES = wtypes.Enum(wtypes.text,
                                  *CONF.collect.services)


class ResourceDescriptor(wtypes.Base):

    service = CLOUDKITTY_SERVICES

    # FIXME(sheeprine): values should be dynamic
    # Testing with ironic dynamic type
    desc = {wtypes.text: cktypes.MultiType(wtypes.text, int, float, dict)}

    volume = int

    def to_json(self):
        res_dict = {}
        res_dict[self.service] = [{'desc': self.desc,
                                   'vol': {'qty': self.volume,
                                           'unit': 'undef'}
                                   }]
        return res_dict


class ModulesController(rest.RestController):

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
            if not hasattr(self, ext.name):
                setattr(self, ext.name, ext.obj.controller())

    @wsme_pecan.wsexpose([wtypes.text])
    def get(self):
        return [ext for ext in self.extensions.names()]


class BillingController(rest.RestController):

    _custom_actions = {
        'quote': ['POST'],
    }

    modules = ModulesController()

    @wsme_pecan.wsexpose(float, body=[ResourceDescriptor])
    def quote(self, res_data):
        # TODO(sheeprine): Send RPC request for quote
        from cloudkitty import extension_manager
        b_processors = {}
        processors = extension_manager.EnabledExtensionManager(
            'cloudkitty.billing.processors',
        )

        for processor in processors:
            b_name = processor.name
            b_obj = processor.obj
            b_processors[b_name] = b_obj

        res_dict = {}
        for res in res_data:
            if res.service not in res_dict:
                res_dict[res.service] = []
            json_data = res.to_json()
            res_dict[res.service].extend(json_data[res.service])

        for processor in b_processors.values():
            processor.process([{'usage': res_dict}])

        price = 0.0
        for res in res_dict.values():
            for data in res:
                price += data.get('billing', {}).get('price', 0.0)
        return price


class ReportController(rest.RestController):

    _custom_actions = {
        'total': ['GET']
    }

    @wsme_pecan.wsexpose(float)
    def total(self):
        # TODO(sheeprine): Get current total from DB
        return 10.0


class V1Controller(rest.RestController):

    billing = BillingController()
    report = ReportController()