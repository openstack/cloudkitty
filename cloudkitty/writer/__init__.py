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
import abc

import six

from cloudkitty import state
from cloudkitty import utils as ck_utils


@six.add_metaclass(abc.ABCMeta)
class BaseReportWriter(object):
    """Base report writer."""
    report_type = None

    def __init__(self, write_orchestrator, tenant_id, backend, basepath=None):
        self._write_orchestrator = write_orchestrator
        self._backend = backend
        self._tenant_id = tenant_id
        self._sm = state.DBStateManager(self._tenant_id,
                                        self.report_type)
        self._report = None
        self._period = 3600

        self._basepath = basepath

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

    @abc.abstractmethod
    def _gen_filename(self):
        """Filename generation

        """

    def _open(self):
        filename = self._gen_filename()
        self._report = self._backend(filename, 'wb+')
        self._report.seek(0, 2)

    def _get_report_size(self):
        return self._report.tell()

    @abc.abstractmethod
    def _recover_state(self):
        """Recover state from a last run.

        """

    def _update_state_manager(self):
        self._sm.set_state(self.usage_end)
        metadata = {'total': self.total}
        self._sm.set_metadata(metadata)

    def _get_state_manager_timeframe(self):
        timeframe = self._sm.get_state()
        self.usage_start = timeframe
        self.usage_start_dt = ck_utils.ts2dt(timeframe)
        self.usage_end = timeframe + self._period
        self.usage_end_dt = ck_utils.ts2dt(self.usage_end)
        metadata = self._sm.get_metadata()
        self.total = metadata.get('total', 0)

    def get_timeframe(self, timeframe):
        return self._write_orchestrator.get_timeframe(timeframe)

    @abc.abstractmethod
    def _write_header(self):
        """Write report headers

        """

    @abc.abstractmethod
    def _write_total(self):
        """Write current total

        """

    @abc.abstractmethod
    def _write(self):
        """Write report content

        """

    def _pre_commit(self):
        if self._report is None:
            self._open()
            if not self.checked_first_line:
                if self._get_report_size() == 0:
                    self._write_header()
                else:
                    self._recover_state()
                self.checked_first_line = True
        else:
            self._recover_state()

    def _commit(self):
        self._pre_commit()

        self._write()
        self._update_state_manager()

        self._post_commit()

    def _post_commit(self):
        self._usage_data = {}
        self._write_total()

    def _update(self, data):
        for service in data:
            if service in self._usage_data:
                self._usage_data[service].extend(data[service])
            else:
                self._usage_data[service] = data[service]
            # Update totals
            for entry in data[service]:
                self.total += entry['rating']['price']

    def append(self, data, start, end):
        # FIXME we should use the real time values
        if self.usage_end is not None and start >= self.usage_end:
            self.usage_start = None

        if self.usage_start is None:
            self.usage_start = start
            self.usage_end = start + self._period
            self.usage_start_dt = ck_utils.ts2dt(self.usage_start)
            self.usage_end_dt = ck_utils.ts2dt(self.usage_end)

        self._update(data)

    def commit(self):
        self._commit()

    @abc.abstractmethod
    def _close_file(self):
        """Close report file

        """

    def close(self):
        self._close_file()
