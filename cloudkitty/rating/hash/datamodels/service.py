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
from wsme import types as wtypes

from cloudkitty.api.v1 import types as ck_types


class Service(wtypes.Base):
    """Type describing a service.

    A service is directly mapped to the usage key, the collected service.
    """

    service_id = wtypes.wsattr(ck_types.UuidType(), mandatory=False)
    """UUID of the service."""

    name = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of the service."""

    @classmethod
    def sample(cls):
        sample = cls(service_id='a733d0e1-1ec9-4800-8df8-671e4affd017',
                     name='compute')
        return sample


class ServiceCollection(wtypes.Base):
    """Type describing a list of services."""

    services = [Service]
    """List of services."""

    @classmethod
    def sample(cls):
        sample = Service.sample()
        return cls(services=[sample])
