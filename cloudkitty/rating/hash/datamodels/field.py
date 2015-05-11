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


class Field(wtypes.Base):
    """Type describing a field.

    A field is mapping a value of the 'desc' dict of the CloudKitty data. It's
    used to map the name of a metadata.
    """

    field_id = wtypes.wsattr(ck_types.UuidType(), mandatory=False)
    """UUID of the field."""

    name = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of the field."""

    service_id = wtypes.wsattr(ck_types.UuidType(), mandatory=True)
    """UUID of the parent service."""

    @classmethod
    def sample(cls):
        sample = cls(field_id='ac55b000-a05b-4832-b2ff-265a034886ab',
                     name='image_id',
                     service_id='a733d0e1-1ec9-4800-8df8-671e4affd017')
        return sample


class FieldCollection(wtypes.Base):
    """Type describing a list of fields.

    """

    fields = [Field]
    """List of fields."""

    @classmethod
    def sample(cls):
        sample = Field.sample()
        return cls(fields=[sample])
