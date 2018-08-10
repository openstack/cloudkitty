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
import collections
import datetime

from cloudkitty.writer import csv_base


class CSVMapped(csv_base.BaseCSVBackend):
    report_type = 'csv'

    def __init__(self, write_orchestrator, user_id, backend, state_backend):
        super(CSVMapped, self).__init__(write_orchestrator,
                                        user_id,
                                        backend,
                                        state_backend)

        # Detailed transform dict
        self._field_map = collections.OrderedDict(
            [('UsageStart', self._trans_get_usage_start),
             ('UsageEnd', self._trans_get_usage_end),
             ('ResourceId', self._trans_res_id),
             ('Operation', self._trans_operation),
             ('UserId', 'desc:user_id'),
             ('ProjectId', 'desc:project_id'),
             ('ItemName', 'desc:name'),
             ('ItemFlavor', 'desc:flavor_name'),
             ('ItemFlavorId', 'desc:flavor_id'),
             ('AvailabilityZone', 'desc:availability_zone'),
             ('Service', self._trans_service),
             ('UsageQuantity', 'vol:qty'),
             ('RateValue', 'rating:price'),
             ('Cost', self._trans_calc_cost),
             ('user:*', 'desc:metadata:*')])

    def _write_total(self):
        lines = [[''] * self._headers_len for i in range(3)]
        for i in range(len(lines)):
            lines[i][1] = self._tenant_id

        lines[1][2] = self._tenant_id

        lines[0][3] = 'InvoiceTotal'
        lines[1][3] = 'AccountTotal'
        lines[2][3] = 'StatementTotal'

        lines[0][5] = 'Total amount for invoice'
        lines[1][5] = 'Total for linked account# {}'.format(self._tenant_id)
        start_month = datetime.datetime(
            self.usage_start_dt.year,
            self.usage_start_dt.month,
            1)
        lines[2][5] = ('Total statement amount for period '
                       '{} - {}').format(self._format_date(start_month),
                                         self._get_usage_end())

        lines[0][8] = self.total
        lines[1][8] = self.total
        lines[2][8] = self.total

        self._csv_report.writerows(lines)

    @staticmethod
    def _format_date(raw_dt):
        return raw_dt.strftime('%Y/%m/%d %H:%M:%S')

    def _get_usage_start(self):
        """Get the start usage of this period.

        """
        if self.cached_start == self.usage_start:
            return self.cached_start_str
        else:
            self.cached_start = self.usage_start
            self.cached_start_str = self._format_date(self.usage_start_dt)
            return self.cached_start_str

    def _get_usage_end(self):
        """Get the end usage of this period.

        """
        if self.cached_start == self.usage_start and self.cached_end_str \
           and self.cached_end > self.cached_start:
            return self.cached_end_str
        else:
            usage_end = self.usage_start_dt + datetime.timedelta(
                seconds=self._period)
            self.cached_end_str = self._format_date(usage_end)
            return self.cached_end_str

    def _trans_get_usage_start(self, _context, _report_data):
        """Dummy transformation function to comply with the standard.

        """
        return self._get_usage_start()

    def _trans_get_usage_end(self, _context, _report_data):
        """Dummy transformation function to comply with the standard.

        """
        return self._get_usage_end()

    def _trans_product_name(self, context, _report_data):
        """Context dependent product name translation.

        """
        if context == 'compute' or context == 'instance':
            return 'Nova Computing'
        else:
            return context

    def _trans_operation(self, context, _report_data):
        """Context dependent operation translation.

        """
        if context == 'compute' or context == 'instance':
            return 'RunInstances'

    def _trans_res_id(self, context, report_data):
        """Context dependent resource id transformation function.

        """
        return report_data['desc'].get('resource_id')

    def _trans_calc_cost(self, context, report_data):
        """Cost calculation function.

        """
        try:
            quantity = report_data['vol'].get('qty')
            rate = report_data['rating'].get('price')
            return str(float(quantity) * rate)
        except TypeError:
            pass

    def _trans_service(self, context, report_data):
        return context
