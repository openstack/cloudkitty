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

from cloudkitty.api.v1.datamodels import report as report_models
from cloudkitty.common import policy
from cloudkitty import utils as ck_utils


class ReportController(rest.RestController):
    """REST Controller managing the reporting.

    """

    _custom_actions = {
        'total': ['GET'],
        'tenants': ['GET'],
        'summary': ['GET']
    }

    @wsme_pecan.wsexpose([wtypes.text],
                         datetime.datetime,
                         datetime.datetime)
    def tenants(self, begin=None, end=None):
        """Return the list of rated tenants.

        """
        policy.authorize(pecan.request.context, 'report:list_tenants', {})

        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        storage = pecan.request.storage_backend
        tenants = storage.get_tenants(begin, end)
        return tenants

    @wsme_pecan.wsexpose(decimal.Decimal,
                         datetime.datetime,
                         datetime.datetime,
                         wtypes.text,
                         wtypes.text,
                         bool)
    def total(self, begin=None, end=None, tenant_id=None, service=None,
              all_tenants=False):
        """Return the amount to pay for a given period.

        """
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        if all_tenants:
            tenant_id = None
        else:
            tenant_context = pecan.request.context.tenant
            tenant_id = tenant_context if not tenant_id else tenant_id
        policy.authorize(pecan.request.context, 'report:get_total',
                         {"tenant_id": tenant_id})

        storage = pecan.request.storage_backend
        # FIXME(sheeprine): We should filter on user id.
        # Use keystone token information by default but make it overridable and
        # enforce it by policy engine
        total = storage.get_total(begin, end, tenant_id, service)

        # TODO(Aaron): `get_total` return a list of dict,
        # Get value of rate from index[0]
        total = total[0].get('rate', decimal.Decimal('0'))
        return total if total else decimal.Decimal('0')

    @wsme_pecan.wsexpose(report_models.SummaryCollectionModel,
                         datetime.datetime,
                         datetime.datetime,
                         wtypes.text,
                         wtypes.text,
                         wtypes.text,
                         bool)
    def summary(self, begin=None, end=None, tenant_id=None,
                service=None, groupby=None, all_tenants=False):
        """Return the summary to pay for a given period.

        """
        if not begin:
            begin = ck_utils.get_month_start()
        if not end:
            end = ck_utils.get_next_month()

        if all_tenants:
            tenant_id = None
        else:
            tenant_context = pecan.request.context.tenant
            tenant_id = tenant_context if not tenant_id else tenant_id
        policy.authorize(pecan.request.context, 'report:get_summary',
                         {"tenant_id": tenant_id})
        storage = pecan.request.storage_backend

        summarymodels = []
        results = storage.get_total(begin, end, tenant_id, service,
                                    groupby=groupby)
        for result in results:
            summarymodel = report_models.SummaryModel(**result)
            summarymodels.append(summarymodel)

        return report_models.SummaryCollectionModel(summary=summarymodels)
