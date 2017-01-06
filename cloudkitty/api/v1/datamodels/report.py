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
# @author: Aaron.Ding(dinghh@awcloud.com)
#
import datetime

from wsme import types as wtypes


class SummaryModel(wtypes.Base):
    """Type describing a report summary info."""

    begin = datetime.datetime
    """Begin date for the sample."""

    end = datetime.datetime
    """End date for the sample."""

    tenant_id = wtypes.text
    """Tenant owner of the sample."""

    res_type = wtypes.text
    """Resource type of the sample."""

    rate = wtypes.text
    """summary rate of the sample"""

    def __init__(self, begin=None, end=None, tenant_id=None,
                 res_type=None, rate=None):
        self.begin = begin
        self.end = end
        self.tenant_id = tenant_id if tenant_id else "ALL"
        self.res_type = res_type if res_type else "ALL"
        # TODO(Aaron): Need optimize, control precision with decimal
        self.rate = str(float('%0.5f' % rate)) if rate else "0"

    def to_json(self):
        return {'begin': self.begin,
                'end': self.end,
                'tenant_id': self.tenant_id,
                'res_type': self.res_type,
                'rate': self.rate}

    @classmethod
    def sample(cls):
        sample = cls(tenant_id='69d12143688f413cbf5c3cfe03ed0a12',
                     begin=datetime.datetime(2015, 4, 22, 7),
                     end=datetime.datetime(2015, 4, 22, 8),
                     res_type='compute',
                     rate="1")
        return sample


class SummaryCollectionModel(wtypes.Base):
    """A list of report summary."""

    summary = [SummaryModel]

    @classmethod
    def sample(cls):
        sample = SummaryModel.sample()
        return cls(summary=[sample])
