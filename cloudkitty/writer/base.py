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

from cloudkitty import state


class BaseReportWriter(object):
    """Base report writer."""
    report_type = None

    def __init__(self, write_orchestrator, user_id, backend, state_backend):
        self._write_orchestrator = write_orchestrator
        self._write_backend = backend
        self._uid = user_id
        self._sm = state.StateManager(state_backend,
                                      None,
                                      self._uid,
                                      self.report_type)
        self._report = None
        self.period = 3600

        # State vars
        self.checked_first_line = False
        self.usage_start = None
        self.usage_start_dt = None
        self.usage_end = None
        self.usage_end_dt = None

        # Current total
        self.total = 0

        # Current usage period lines
        self._usage_data = {}

    def _gen_filename(self):
        raise NotImplementedError()

    def _open(self):
        filename = self._gen_filename()
        self._report = self._write_backend(filename, 'wb+')
        self._report.seek(0, 2)

    def _get_report_size(self):
        return self._report.tell()

    def _recover_state(self):
        raise NotImplementedError()

    def _update_state_manager(self):
        self._sm.set_state(self.usage_end)
        metadata = {'total': self.total}
        self._sm.set_metadata(metadata)

    def _get_state_manager_timeframe(self):
        timeframe = self._sm.get_state()
        self.usage_start = timeframe
        self.usage_start_dt = datetime.datetime.fromtimestamp(timeframe)
        end_frame = timeframe + self._period
        self.usage_end = datetime.datetime.fromtimestamp(end_frame)
        metadata = self._sm.get_metadata()
        self.total = metadata.get('total', 0)

    def get_timeframe(self, timeframe):
        return self._write_orchestrator.get_timeframe(timeframe)

    def _write_header(self):
        raise NotImplementedError()

    def _write(self):
        raise NotImplementedError()

    def _pre_commit(self):
        if self._report is None:
            self._open()
            if not self.checked_first_line:
                if self._get_report_size() == 0:
                    self._write_header()
                else:
                    self._recover_state()
                self.checked_first_line = True

    def _commit(self):
        self._pre_commit()

        self._write()
        self._update_state_manager()

        self._post_commit()

    def _post_commit(self):
        self._usage_data = {}

    def _update(self, data):
        for service in data:
            if service in self._usage_data:
                self._usage_data[service].extend(data[service])
            else:
                self._usage_data[service] = data[service]
            # Update totals
            for entry in data[service]:
                self.total += entry['billing']['price']

    def append(self, data, start, end):
        # FIXME we should use the real time values
        if self.usage_end is not None and start >= self.usage_end:
            self._commit()
            self.usage_start = None

        if self.usage_start is None:
            self.usage_start = start
            self.usage_end = start + self.period
            self.usage_start_dt = datetime.fromtimestamp(self.usage_start)
            self.usage_end_dt = datetime.fromtimestamp(self.usage_end)

        self._update(data)

    def commit(self):
        self._commit()

    def _close_file(self):
        raise NotImplementedError()

    def close(self):
        self._close_file()
