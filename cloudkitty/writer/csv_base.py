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
import csv
import datetime
import os

from cloudkitty import utils as ck_utils
from cloudkitty import writer


class InconsistentHeaders(Exception):
    pass


class BaseCSVBackend(writer.BaseReportWriter):
    """Report format writer:

        Generates report in csv format
    """
    report_type = 'csv'

    def __init__(self, write_orchestrator, user_id, backend, basepath):
        super(BaseCSVBackend, self).__init__(write_orchestrator,
                                             user_id,
                                             backend,
                                             basepath)

        # Detailed transform OrderedDict
        self._field_map = collections.OrderedDict()

        self._headers = []
        self._headers_len = 0
        self._extra_headers = []
        self._extra_headers_len = 0

        # File vars
        self._csv_report = None

        # State variables
        self.cached_start = None
        self.cached_start_str = ''
        self.cached_end = None
        self.cached_end_str = ''
        self._crumpled = False

        # Current usage period lines
        self._usage_data = []

    def _gen_filename(self, timeframe):
        filename = ('{}-{}-{:02d}.csv').format(self._tenant_id,
                                               timeframe.year,
                                               timeframe.month)
        if self._basepath:
            filename = os.path.join(self._basepath, filename)
        return filename

    def _open(self):
        filename = self._gen_filename(self.usage_start_dt)
        self._report = self._backend(filename, 'rb+')
        self._csv_report = csv.writer(self._report)
        self._report.seek(0, 2)

    def _close_file(self):
        if self._report is not None:
            self._report.close()

    def _get_state_manager_timeframe(self):
        if self.report_type is None:
            raise NotImplementedError()

    def _update_state_manager(self):
        if self.report_type is None:
            raise NotImplementedError()

        super(BaseCSVBackend, self)._update_state_manager()

        metadata = {'total': self.total}
        metadata['headers'] = self._extra_headers
        self._sm.set_metadata(metadata)

    def _init_headers(self):
        headers = self._field_map.keys()
        for header in headers:
            if ':*' in header:
                continue
            self._headers.append(header)
        self._headers_len = len(self._headers)

    def _write_header(self):
        self._csv_report.writerow(self._headers + self._extra_headers)

    def _write(self):
        self._csv_report.writerows(self._usage_data)

    def _post_commit(self):
        self._crumpled = False
        self._usage_data = []
        self._write_total()

    def _update(self, data):
        """Dispatch report data with context awareness.

        """
        if self._crumpled:
            return
        try:
            for service in data:
                for report_data in data[service]:
                    self._process_data(service, report_data)
                    self.total += report_data['rating']['price']
        except InconsistentHeaders:
            self._crumple()
            self._crumpled = True

    def _recover_state(self):
        # Rewind 3 lines
        self._report.seek(0, 2)
        buf_size = self._report.tell()
        if buf_size > 2000:
            buf_size = 2000
        elif buf_size == 0:
            return
        self._report.seek(-buf_size, 2)
        end_buf = self._report.read()
        last_line = buf_size
        for dummy in range(4):
            last_line = end_buf.rfind('\n', 0, last_line)
        if last_line > 0:
            last_line -= len(end_buf) - 1
        else:
            raise RuntimeError('Unable to recover file state.')
        self._report.seek(last_line, 2)
        self._report.truncate()

    def _crumple(self):
        # Reset states
        self._usage_data = []
        self.total = 0

        # Recover state from file
        if self._report is not None:
            self._report.seek(0)
            reader = csv.reader(self._report)
            # Skip header
            for dummy in range(2):
                line = reader.next()
            self.usage_start_dt = datetime.datetime.strptime(
                line[0],
                '%Y/%m/%d %H:%M:%S')
            self.usage_start = ck_utils.dt2ts(self.usage_start_dt)
            self.usage_end_dt = datetime.datetime.strptime(
                line[1],
                '%Y/%m/%d %H:%M:%S')
            self.usage_end = ck_utils.dt2ts(self.usage_end_dt)

            # Reset file
            self._report.seek(0)
            self._report.truncate()
            self._write_header()

        timeframe = self._write_orchestrator.get_timeframe(
            self.usage_start)
        start = self.usage_start
        self.usage_start = None
        for data in timeframe:
            self.append(data['usage'],
                        start,
                        None)
        self.usage_start = self.usage_end

    def _update_extra_headers(self, new_head):
        self._extra_headers.append(new_head)
        self._extra_headers.sort()
        self._extra_headers_len += 1

    def _allocate_extra(self, line):
        for dummy in range(self._extra_headers_len):
            line.append('')

    def _map_wildcard(self, base, report_data):
        wildcard_line = []
        headers_changed = False
        self._allocate_extra(wildcard_line)
        base_section, dummy = base.split(':')
        if not report_data:
            return []
        for field in report_data:
            col_name = base_section + ':' + field
            if col_name not in self._extra_headers:
                self._update_extra_headers(col_name)
                headers_changed = True
            else:
                idx = self._extra_headers.index(col_name)
                wildcard_line[idx] = report_data[field]
        if headers_changed:
            raise InconsistentHeaders('Headers value changed'
                                      ', need to rebuild.')
        return wildcard_line

    def _recurse_sections(self, sections, data):
        if not sections.count(':'):
            return data.get(sections, '')
        fields = sections.split(':')
        cur_data = data
        for field in fields:
            if field in cur_data:
                cur_data = cur_data[field]
            else:
                return None
        return cur_data

    def _process_data(self, context, report_data):
        """Transform the raw json data to the final CSV values.

        """
        if not self._headers_len:
            self._init_headers()

        formated_data = []
        for base, mapped in self._field_map.iteritems():
            final_data = ''
            if isinstance(mapped, str):
                mapped_section, mapped_field = mapped.rsplit(':', 1)
                data = self._recurse_sections(mapped_section, report_data)
                if mapped_field == '*':
                    extra_fields = self._map_wildcard(base, data)
                    formated_data.extend(extra_fields)
                    continue
                elif mapped_section in report_data:
                    data = report_data[mapped_section]
                    if mapped_field in data:
                        final_data = data[mapped_field]
            elif mapped is not None:
                final_data = mapped(context, report_data)
            formated_data.append(final_data)

        self._usage_data.append(formated_data)
