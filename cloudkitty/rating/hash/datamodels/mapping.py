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
import decimal

from wsme import types as wtypes

from cloudkitty.api.v1 import types as ck_types

MAP_TYPE = wtypes.Enum(wtypes.text, 'flat', 'rate')


class Mapping(wtypes.Base):
    """Type describing a Mapping.

    A mapping is used to apply rating rules based on a value, if the parent is
    a field then it's check the value of a metadata. If it's a service then it
    directly apply the rate to the volume.
    """

    mapping_id = wtypes.wsattr(ck_types.UuidType(), mandatory=False)
    """UUID of the mapping."""

    value = wtypes.wsattr(wtypes.text, mandatory=False, default='')
    """Key of the mapping."""

    map_type = wtypes.wsattr(MAP_TYPE, default='flat', name='type')
    """Type of the mapping."""

    cost = wtypes.wsattr(decimal.Decimal, mandatory=True)
    """Value of the mapping."""

    service_id = wtypes.wsattr(ck_types.UuidType(),
                               mandatory=False)
    """UUID of the service."""

    field_id = wtypes.wsattr(ck_types.UuidType(),
                             mandatory=False)
    """UUID of the field."""

    group_id = wtypes.wsattr(ck_types.UuidType(),
                             mandatory=False)
    """UUID of the hashmap group."""

    tenant_id = wtypes.wsattr(ck_types.UuidType(),
                              mandatory=False,
                              default=None)
    """UUID of the hashmap tenant."""

    @classmethod
    def sample(cls):
        sample = cls(mapping_id='39dbd39d-f663-4444-a795-fb19d81af136',
                     field_id='ac55b000-a05b-4832-b2ff-265a034886ab',
                     value='m1.micro',
                     map_type='flat',
                     cost=decimal.Decimal('4.2'),
                     tenant_id='7977999e-2e25-11e6-a8b2-df30b233ffcb')
        return sample


class MappingCollection(wtypes.Base):
    """Type describing a list of mappings.

    """

    mappings = [Mapping]
    """List of mappings."""

    @classmethod
    def sample(cls):
        sample = Mapping.sample()
        return cls(mappings=[sample])
