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
import decimal
import json
import os

from cloudkitty import writer


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


class OSRFBackend(writer.BaseReportWriter):
    """OpenStack Report Format Writer:

        Generates report in native format (json)
    """
    report_type = 'osrf'

    def _gen_filename(self, timeframe):
        filename = '{}-osrf-{}-{:02d}.json'.format(self._tenant_id,
                                                   timeframe.year,
                                                   timeframe.month)
        if self._basepath:
            filename = os.path.join(self._basepath, filename)
        return filename

    def _open(self):
        filename = self._gen_filename(self.usage_start_dt)
        self._report = self._backend(filename, 'rb+')
        self._report.seek(0, 2)
        if self._report.tell():
            self._recover_state()
        else:
            self._report.seek(0)

    def _write_header(self):
        self._report.write('[')
        self._report.flush()

    def _write_total(self):
        total = {'total': self.total}
        self._report.write(json.dumps(total, cls=DecimalEncoder))
        self._report.write(']')
        self._report.flush()

    def _recover_state(self):
        # Search for last comma
        self._report.seek(0, 2)
        max_idx = self._report.tell()
        if max_idx > 2000:
            max_idx = 2000
        hay = ''
        for idx in range(10, max_idx, 10):
            self._report.seek(-idx, 2)
            hay = self._report.read()
            if hay.count(','):
                break
        last_comma = hay.rfind(',')
        if last_comma > -1:
            last_comma -= len(hay)
        else:
            raise RuntimeError('Unable to recover file state.')
        self._report.seek(last_comma, 2)
        self._report.write(', ')
        self._report.truncate()

    def _close_file(self):
        if self._report is not None:
            self._recover_state()
            self._write_total()
            self._report.close()

    def _write(self):
        data = {}
        data['period'] = {'begin': self.usage_start_dt.isoformat(),
                          'end': self.usage_end_dt.isoformat()}
        data['usage'] = self._usage_data

        self._report.write(json.dumps(data, cls=DecimalEncoder))
        self._report.write(', ')
        self._report.flush()
