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
import copy

from oslo_config import cfg
from oslo_utils import fileutils
from stevedore import named

from cloudkitty import state
from cloudkitty import storage
from cloudkitty import storage_state
from cloudkitty import utils as ck_utils

CONF = cfg.CONF
WRITERS_NAMESPACE = 'cloudkitty.output.writers'


class WriteOrchestrator(object):
    """Write Orchestrator:

        Handle incoming data from the global orchestrator, and store them in an
        intermediary data format before final transformation.
    """
    def __init__(self,
                 backend,
                 tenant_id,
                 storage,
                 basepath=None,
                 period=3600):
        self._backend = backend
        self._tenant_id = tenant_id
        self._storage = storage
        self._storage_state = storage_state.StateManager()
        self._basepath = basepath
        if self._basepath:
            fileutils.ensure_tree(self._basepath)
        self._period = period
        self._sm = state.DBStateManager(self._tenant_id,
                                        'writer_status')
        self._write_pipeline = []

        # State vars
        self.usage_start = None
        self.usage_end = None

        # Current total
        self.total = 0

    def init_writing_pipeline(self):
        CONF.import_opt('pipeline', 'cloudkitty.config', 'output')
        output_pipeline = named.NamedExtensionManager(
            WRITERS_NAMESPACE,
            CONF.output.pipeline)
        for writer in output_pipeline:
            self.add_writer(writer.plugin)

    def add_writer(self, writer_class):
        writer = writer_class(self,
                              self._tenant_id,
                              self._backend,
                              self._basepath)
        self._write_pipeline.append(writer)

    def _update_state_manager_data(self):
        self._sm.set_state(self.usage_end)
        metadata = {'total': self.total}
        self._sm.set_metadata(metadata)

    def _load_state_manager_data(self):
        timeframe = self._sm.get_state()
        if timeframe:
            self.usage_start = timeframe
            self.usage_end = self.usage_start + self._period
        metadata = self._sm.get_metadata()
        if metadata:
            self.total = metadata.get('total', 0)

    def _dispatch(self, data):
        for service in data:
            # Update totals
            for entry in data[service]:
                self.total += entry['rating']['price']
        # Dispatch data to writing pipeline
        for backend in self._write_pipeline:
            backend.append(data, self.usage_start, self.usage_end)

    def get_timeframe(self, timeframe, timeframe_end=None):
        if not timeframe_end:
            timeframe_end = timeframe + self._period
        try:
            group_filters = {'project_id': self._tenant_id}
            data = self._storage.retrieve(begin=timeframe,
                                          end=timeframe_end,
                                          group_filters=group_filters,
                                          paginate=False)
            for df in data['dataframes']:
                for service, resources in df['usage'].items():
                    for resource in resources:
                        resource['desc'] = copy.deepcopy(resource['metadata'])
                        resource['desc'].update(resource['groupby'])
        except storage.NoTimeFrame:
            return None
        return data

    def close(self):
        for writer in self._write_pipeline:
            writer.close()

    def _push_data(self):
        data = self.get_timeframe(self.usage_start, self.usage_end)
        if data and data['total'] > 0:
            for timeframe in data['dataframes']:
                self._dispatch(timeframe['usage'])
            return True
        else:
            return False

    def _commit_data(self):
        for backend in self._write_pipeline:
            backend.commit()

    def reset_state(self):
        self._load_state_manager_data()
        self.usage_end = self._storage_state.get_state()
        self._update_state_manager_data()

    def restart_month(self):
        self._load_state_manager_data()
        month_start = ck_utils.get_month_start()
        self.usage_end = ck_utils.dt2ts(month_start)
        self._update_state_manager_data()

    def process(self):
        self._load_state_manager_data()
        storage_state = self._storage_state.get_state(self._tenant_id)
        if not self.usage_start:
            self.usage_start = storage_state
            self.usage_end = self.usage_start + self._period
        while storage_state > self.usage_start:
            if self._push_data():
                self._commit_data()
            self._update_state_manager_data()
            self._load_state_manager_data()
            storage_state = self._storage_state.get_state(self._tenant_id)
        self.close()
