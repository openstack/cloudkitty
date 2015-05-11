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


class Group(wtypes.Base):
    """Type describing a group.

    A group is used to divide calculations. It can be used to create a group
    for the instance rating (flavor) and one if we have premium images
    (image_id). So you can take into account multiple parameters during the
    rating.
    """

    group_id = wtypes.wsattr(ck_types.UuidType(), mandatory=False)
    """UUID of the group."""

    name = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of the group."""

    @classmethod
    def sample(cls):
        sample = cls(group_id='afe898cb-86d8-4557-ad67-f4f01891bbee',
                     name='instance_rating')
        return sample


class GroupCollection(wtypes.Base):
    """Type describing a list of groups.

    """

    groups = [Group]
    """List of groups."""

    @classmethod
    def sample(cls):
        sample = Group.sample()
        return cls(groups=[sample])
