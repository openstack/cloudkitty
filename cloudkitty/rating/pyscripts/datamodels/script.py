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


class Script(wtypes.Base):
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
        sample = cls(script_id='bc05108d-f515-4984-8077-de319cbf35aa',
                     name='policy1',
                     data='return 0',
                     checksum='da39a3ee5e6b4b0d3255bfef95601890afd80709')
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
