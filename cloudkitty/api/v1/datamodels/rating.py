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
import decimal

from oslo_config import cfg
from oslo_log import log
from wsme import types as wtypes

from cloudkitty.api.v1 import types as cktypes

LOG = log.getLogger(__name__)

CONF = cfg.CONF


class CloudkittyResource(wtypes.Base):
    """Type describing a resource in CloudKitty.

    """

    service = wtypes.text
    """Name of the service."""

    # FIXME(sheeprine): values should be dynamic
    # Testing with ironic dynamic type
    desc = {wtypes.text: cktypes.MultiType(wtypes.text, int, float,
                                           dict, decimal.Decimal)}
    """Description of the resources parameters."""

    volume = decimal.Decimal
    """Volume of resources."""

    def to_json(self):
        res_dict = {}
        res_dict[self.service] = [{'desc': self.desc,
                                   'vol': {'qty': str(self.volume),
                                           'unit': 'undef'}
                                   }]
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(service='compute',
                     desc={
                         'image_id': 'a41fba37-2429-4f15-aa00-b5bc4bf557bf'
                     },
                     volume=decimal.Decimal(1))
        return sample


class CloudkittyResourceCollection(wtypes.Base):
    """A list of CloudKittyResources."""

    resources = [CloudkittyResource]


class CloudkittyModule(wtypes.Base):
    """A rating extension summary

    """

    module_id = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of the extension."""

    description = wtypes.wsattr(wtypes.text, mandatory=False)
    """Short description of the extension."""

    enabled = wtypes.wsattr(bool)
    """Extension status."""

    hot_config = wtypes.wsattr(bool, default=False, name='hot-config')
    """On-the-fly configuration support."""

    priority = wtypes.wsattr(int)
    """Priority of the extension."""

    @classmethod
    def sample(cls):
        sample = cls(name='example',
                     description='Sample extension.',
                     enabled=True,
                     hot_config=False,
                     priority=2)
        return sample


class CloudkittyModuleCollection(wtypes.Base):
    """A list of rating extensions."""

    modules = [CloudkittyModule]
