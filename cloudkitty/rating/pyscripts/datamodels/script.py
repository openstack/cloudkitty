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
from wsme import types as wtypes

from cloudkitty.api.v1 import types as ck_types
from cloudkitty.rating.common.datamodels.models import VolatileAuditableModel


class Script(VolatileAuditableModel):
    """Type describing a script.

    """

    script_id = wtypes.wsattr(ck_types.UuidType(), mandatory=False)
    """UUID of the script."""

    name = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of the script."""

    data = wtypes.wsattr(wtypes.text, mandatory=False)
    """Data of the script."""

    checksum = wtypes.wsattr(wtypes.text, mandatory=False, readonly=True)
    """Checksum of the script data."""

    @classmethod
    def sample(cls):
        sample = super().sample()
        sample = cls(script_id='bc05108d-f515-4984-8077-de319cbf35aa',
                     name='policy1',
                     data='return 0',
                     checksum='cf83e1357eefb8bdf1542850d66d8007d620e4050b5715d'
                              'c83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec'
                              '2f63b931bd47417a81a538327af927da3e',
                     **sample.__dict__)
        return sample


class ScriptCollection(wtypes.Base):
    """Type describing a list of scripts.

    """

    scripts = [Script]
    """List of scripts."""

    @classmethod
    def sample(cls):
        sample = Script.sample()
        return cls(scripts=[sample])
