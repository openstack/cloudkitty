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
import datetime
import decimal

from wsme import types as wtypes

from cloudkitty.api.v1.datamodels import rating as rating_resources


class RatedResource(rating_resources.CloudkittyResource):
    """Represents a rated CloudKitty resource."""

    rating = decimal.Decimal

    def to_json(self):
        res_dict = super(RatedResource, self).to_json()
        res_dict['rating'] = self.rating
        return res_dict

    @classmethod
    def sample(cls):
        sample = cls(volume=decimal.Decimal('1.0'),
                     service='compute',
                     rating=decimal.Decimal('1.0'),
                     desc={'flavor': 'm1.tiny', 'vcpus': '1'})
        return sample


class DataFrame(wtypes.Base):
    """Type describing a stored data frame."""

    begin = datetime.datetime
    """Begin date for the sample."""

    end = datetime.datetime
    """End date for the sample."""

    tenant_id = wtypes.text
    """Tenant owner of the sample."""

    resources = [RatedResource]
    """A resource list."""

    def to_json(self):
        return {'begin': self.begin,
                'end': self.end,
                'tenant_id': self.tenant_id,
                'resources': self.resources}

    @classmethod
    def sample(cls):
        res_sample = RatedResource.sample()
        sample = cls(tenant_id='69d12143688f413cbf5c3cfe03ed0a12',
                     begin=datetime.datetime(2015, 4, 22, 7),
                     end=datetime.datetime(2015, 4, 22, 8),
                     resources=[res_sample])
        return sample


class DataFrameCollection(wtypes.Base):
    """A list of stored data frames."""

    dataframes = [DataFrame]

    @classmethod
    def sample(cls):
        sample = DataFrame.sample()
        return cls(dataframes=[sample])
