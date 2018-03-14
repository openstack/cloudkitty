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
from wsme import types as wtypes


class CollectorInfos(wtypes.Base):
    """Type describing a collector module.

    """

    name = wtypes.wsattr(wtypes.text, mandatory=False)
    """Name of the collector."""

    enabled = wtypes.wsattr(bool, mandatory=True)
    """State of the collector."""

    def to_json(self):
        res_dict = {'name': self.name,
                    'enabled': self.enabled}
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(name='gnocchi',
                     enabled=True)
        return sample


class ServiceToCollectorMapping(wtypes.Base):
    """Type describing a service to collector mapping.

    """

    service = wtypes.text
    """Name of the service."""

    collector = wtypes.text
    """Name of the collector."""

    def to_json(self):
        res_dict = {'service': self.service,
                    'collector': self.collector}
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(service='compute',
                     collector='gnocchi')
        return sample


class ServiceToCollectorMappingCollection(wtypes.Base):
    """Type describing a service to collector mapping collection.

    """

    mappings = [ServiceToCollectorMapping]
    """List of service to collector mappings."""

    def to_json(self):
        res_dict = {'mappings': self.mappings}
        return res_dict

    @classmethod
    def sample(cls):
        mapping = ServiceToCollectorMapping(service='compute',
                                            collector='gnocchi')
        sample = cls(mappings=[mapping])
        return sample
