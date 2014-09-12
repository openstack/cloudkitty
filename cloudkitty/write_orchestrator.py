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
import json
import os.path
import zipfile

import cloudkitty.utils as utils


class OSRTFBackend(object):
    """Native backend for transient report storage.

    Used to store data from the output of the billing pipeline.
    """

    def __init__(self):
        self._osrtf = None

    def open(self, filename):
        # FIXME(sheeprine): ZipFile is working well with filename
        # but not backend
        self._osrtf = zipfile.ZipFile(filename, 'a')

    def _gen_filename(self, timeframe):
        filename = '{}-{:02d}-{:02d}-{}-{}.json'.format(timeframe.year,
                                                        timeframe.month,
                                                        timeframe.day,
                                                        timeframe.hour,
                                                        timeframe.minute)
        return filename

    def _file_exists(self, filename):
        for file_info in self._osrtf.infolist():
            if file_info.filename == filename:
                return True
        return False

    def add(self, timeframe, data):
        """Add the data to the OpenStack Report Transient Format."""
        filename = self._gen_filename(timeframe)
        # We can only check for the existence of a file not rewrite or delete
        # it
        if not self._file_exists(filename):
            self._osrtf.writestr(filename, json.dumps(data))

    def get(self, timeframe):
        try:
            filename = self._gen_filename(timeframe)
            data = json.loads(self._osrtf.read(filename))
            return data
        except Exception:
            pass

    def close(self):
        self._osrtf.close()


class WriteOrchestrator(object):
    """Write Orchestrator:

        Handle incoming data from the global orchestrator, and store them in an
        intermediary data format before final transformation.
    """
    def __init__(self,
                 backend,
                 user_id,
                 state_manager,
                 basepath=None,
                 period=3600):
        self._backend = backend
        self._uid = user_id
        self._period = period
        self._sm = state_manager
        self._basepath = basepath
        self._osrtf = None
        self._write_pipeline = []

        # State vars
        self.usage_start = None
        self.usage_start_dt = None
        self.usage_end = None
        self.usage_end_dt = None

        # Current total
        self.total = 0

        # Current usage period lines
        self._usage_data = {}

    def add_writer(self, writer_class):
        writer = writer_class(self,
                              self._uid,
                              self._backend,
                              self._basepath)
        self._write_pipeline.append(writer)

    def _gen_osrtf_filename(self, timeframe):
        if not isinstance(timeframe, datetime.datetime):
            raise TypeError('timeframe should be of type datetime.')
        date = '{}-{:02d}'.format(timeframe.year, timeframe.month)
        filename = '{}-osrtf-{}.zip'.format(self._uid, date)
        return filename

    def _update_state_manager(self):
        self._sm.set_state(self.usage_end)
        metadata = {'total': self.total}
        self._sm.set_metadata(metadata)

    def _get_state_manager_timeframe(self):
        timeframe = self._sm.get_state()
        self.usage_start = datetime.datetime.fromtimestamp(timeframe)
        end_frame = timeframe + self._period
        self.usage_end = datetime.datetime.fromtimestamp(end_frame)
        metadata = self._sm.get_metadata()
        self.total = metadata.get('total', 0)

    def _filter_period(self, json_data):
        """Detect the best usage period to extract.

        Removes the usage from the json data and returns it.
        """
        candidate_ts = None
        candidate_idx = 0

        for idx, usage in enumerate(json_data):
            usage_ts = usage['period']['begin']
            if candidate_ts is None or usage_ts < candidate_ts:
                candidate_ts = usage_ts
                candidate_idx = idx

        if candidate_ts:
            return candidate_ts, json_data.pop(candidate_idx)['usage']

    def _format_data(self, timeframe, data):
        beg = utils.dt2ts(timeframe)
        end = beg + self._period
        final_data = {'period': {'begin': beg, 'end': end}}
        final_data['usage'] = data
        return [final_data]

    def _open_osrtf(self):
        if self._osrtf is None:
            self._osrtf = OSRTFBackend()
            filename = self._gen_osrtf_filename(self.usage_start_dt)
            if self._basepath:
                self._osrtf_filename = os.path.join(self._basepath, filename)
        self._osrtf.open(self._osrtf_filename)

    def _pre_commit(self):
        self._open_osrtf()

    def _commit(self):
        self._pre_commit()

        self._osrtf.add(self.usage_start_dt, self._usage_data)

        # Dispatch data to writing pipeline
        for backend in self._write_pipeline:
            backend.append(self._usage_data, self.usage_start, self.usage_end)

        self._update_state_manager()

        self._usage_data = {}

        self._post_commit()

    def _post_commit(self):
        self._osrtf.close()

    def _dispatch(self, data):
        for service in data:
            if service in self._usage_data:
                self._usage_data[service].extend(data[service])
            else:
                self._usage_data[service] = data[service]
            # Update totals
            for entry in data[service]:
                self.total += entry['billing']['price']

    def get_timeframe(self, timeframe):
        self._open_osrtf()
        data = self._osrtf.get(timeframe)
        self._osrtf.close()
        return self._format_data(timeframe, data)

    def append(self, raw_data):
        while raw_data:
            usage_start, data = self._filter_period(raw_data)
            if self.usage_end is not None and usage_start >= self.usage_end:
                self._commit()
                self.usage_start = None

            if self.usage_start is None:
                self.usage_start = usage_start
                self.usage_end = usage_start + self._period
                self.usage_start_dt = (
                    datetime.datetime.fromtimestamp(self.usage_start))
                self.usage_end_dt = (
                    datetime.datetime.fromtimestamp(self.usage_end))

            self._dispatch(data)

    def commit(self):
        self._commit()

    def close(self):
        for writer in self._write_pipeline:
            writer.close()
        if self._osrtf is not None:
            self._osrtf.close()
