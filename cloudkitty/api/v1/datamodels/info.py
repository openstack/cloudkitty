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
from oslo_config import cfg
from wsme import types as wtypes

from cloudkitty import utils as ck_utils

CONF = cfg.CONF

METRICS_CONF = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)

CLOUDKITTY_SERVICES = wtypes.Enum(wtypes.text,
                                  *METRICS_CONF['services'])


class CloudkittyServiceInfo(wtypes.Base):
    """Type describing a service info in CloudKitty.

    """

    service_id = CLOUDKITTY_SERVICES
    """Name of the service."""

    metadata = [wtypes.text]
    """List of service metadata"""

    unit = wtypes.text
    """service unit"""

    def to_json(self):
        res_dict = {}
        res_dict[self.service_id] = [{
            'metadata': self.metadata,
            'unit': self.unit
        }]
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(service_id='compute',
                     metadata=['resource_id', 'flavor', 'availability_zone'],
                     unit='instance')
        return sample


class CloudkittyServiceInfoCollection(wtypes.Base):
    """A list of CloudKittyServiceInfo."""

    services = [CloudkittyServiceInfo]

    @classmethod
    def sample(cls):
        sample = CloudkittyServiceInfo.sample()
        return cls(services=[sample])
