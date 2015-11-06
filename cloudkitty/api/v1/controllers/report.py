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

import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty.common import policy


class ReportController(rest.RestController):
    """REST Controller managing the reporting.

    """

    _custom_actions = {
        'total': ['GET'],
        'tenants': ['GET']
    }

    @wsme_pecan.wsexpose([wtypes.text],
                         datetime.datetime,
                         datetime.datetime)
    def tenants(self, begin=None, end=None):
        """Return the list of rated tenants.

        """
        policy.enforce(pecan.request.context, 'report:list_tenants', {})
        storage = pecan.request.storage_backend
        tenants = storage.get_tenants(begin, end)
        return tenants

    @wsme_pecan.wsexpose(decimal.Decimal,
                         datetime.datetime,
                         datetime.datetime,
                         wtypes.text,
                         wtypes.text)
    def total(self, begin=None, end=None, tenant_id=None, service=None):
        """Return the amount to pay for a given period.

        """
        policy.enforce(pecan.request.context, 'report:get_total', {})
        storage = pecan.request.storage_backend
        # FIXME(sheeprine): We should filter on user id.
        # Use keystone token information by default but make it overridable and
        # enforce it by policy engine
        total = storage.get_total(begin, end, tenant_id, service)
        return total if total else decimal.Decimal('0')
