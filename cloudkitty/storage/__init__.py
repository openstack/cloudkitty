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
import datetime

from oslo.config import cfg
import six


storage_opts = [
    cfg.StrOpt('backend',
               default='sqlalchemy',
               help='Name of the storage backend driver.')
]

cfg.CONF.register_opts(storage_opts, group='storage')


@six.add_metaclass(abc.ABCMeta)
class BaseStorage(object):
    """Base Storage class:

        Handle incoming data from the global orchestrator, and store them.
    """
    def __init__(self, period=3600):
        self._period = period

        # State vars
        self.usage_start = None
        self.usage_start_dt = None
        self.usage_end = None
        self.usage_end_dt = None

    @staticmethod
    def init():
        """Initialize storage backend.

        Can be used to create DB schema on first start.
        """
        pass

    def _filter_period(self, json_data):
        """Detect the best usage period to extract.

        Removes the usage from the json data and returns it.
        :param json_data: Data to filter.
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

    def _pre_commit(self):
        """Called before every commit.

        """

    @abc.abstractmethod
    def _commit(self):
        """Push data to the storage backend.

        """

    def _post_commit(self):
        """Called after every commit.

        """

    @abc.abstractmethod
    def _dispatch(self, data):
        """Process rated data.

        :param data: The rated data frames.
        """

    @abc.abstractmethod
    def get_state(self):
        """Return the last written frame's timestamp.

        """

    @abc.abstractmethod
    def get_total(self):
        pass

    @abc.abstractmethod
    def get_time_frame(self, begin, end, **filters):
        """Request a time frame from the storage backend.

        :param begin: When to start filtering.
        :type begin: datetime.datetime
        :param end: When to stop filtering.
        :type end: datetime.datetime
        :param res_type: (Optional) Filter on the resource type.
        :type res_type: str
        """

    def append(self, raw_data):
        """Append rated data before committing them to the backend.

        :param raw_data: The rated data frames.
        """
        while raw_data:
            usage_start, data = self._filter_period(raw_data)
            if self.usage_end is not None and usage_start >= self.usage_end:
                self.commit()
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
        """Commit the changes to the backend.

        """
        self._pre_commit()
        self._commit()
        self._post_commit()
