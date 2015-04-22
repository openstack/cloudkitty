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

from oslo.config import cfg
import six
from stevedore import driver

from cloudkitty import utils as ck_utils

STORAGES_NAMESPACE = 'cloudkitty.storage.backends'
CONF = cfg.CONF

storage_opts = [
    cfg.StrOpt('backend',
               default='sqlalchemy',
               help='Name of the storage backend driver.')
]

CONF.register_opts(storage_opts, group='storage')
CONF.import_opt('period', 'cloudkitty.collector', 'collect')


def get_storage():
    storage_args = {'period': cfg.CONF.collect.period}
    backend = driver.DriverManager(
        STORAGES_NAMESPACE,
        cfg.CONF.storage.backend,
        invoke_on_load=True,
        invoke_kwds=storage_args).driver
    return backend


class NoTimeFrame(Exception):
    """Raised when there is no time frame available."""

    def __init__(self):
        super(NoTimeFrame, self).__init__(
            "No time frame available")


@six.add_metaclass(abc.ABCMeta)
class BaseStorage(object):
    """Base Storage class:

        Handle incoming data from the global orchestrator, and store them.
    """
    def __init__(self, period=CONF.collect.period):
        self._period = period

        # State vars
        self.usage_start = {}
        self.usage_start_dt = {}
        self.usage_end = {}
        self.usage_end_dt = {}
        self._has_data = False

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

    def _pre_commit(self, tenant_id):
        """Called before every commit.

        """

    @abc.abstractmethod
    def _commit(self, tenant_id):
        """Push data to the storage backend.

        """

    def _post_commit(self, tenant_id):
        """Called after every commit.

        """
        self._has_data = False

    @abc.abstractmethod
    def _dispatch(self, data, tenant_id):
        """Process rated data.

        :param data: The rated data frames.
        """

    def _update_start(self, begin, tenant_id):
        """Update usage_start with a new timestamp.

        :param begin: New usage beginning timestamp.
        :param tenant_id: Tenant ID to update.
        """
        self.usage_start[tenant_id] = begin
        self.usage_start_dt[tenant_id] = ck_utils.ts2dt(begin)

    def _update_end(self, end, tenant_id):
        """Update usage_end with a new timestamp.

        :param end: New usage end timestamp.
        :param tenant_id: Tenant ID to update.
        """
        self.usage_end[tenant_id] = end
        self.usage_end_dt[tenant_id] = ck_utils.ts2dt(end)

    def _check_commit(self, usage_start, tenant_id):
        """Check if the period for a given tenant must be committed.

        :param usage_start: Start of the period.
        :param tenant_id: Tenant ID to check for.
        """
        usage_end = self.usage_end.get(tenant_id)
        if usage_end is not None and usage_start >= usage_end:
            self.commit(tenant_id)
            self.usage_start.pop(tenant_id)
        if self.usage_start.get(tenant_id) is None:
            self._update_start(usage_start, tenant_id)
            self._update_end(usage_start + self._period, tenant_id)

    @abc.abstractmethod
    def get_state(self, tenant_id=None):
        """Return the last written frame's timestamp.

        :param tenant_id: Tenant ID to filter on.
        """

    @abc.abstractmethod
    def get_total(self, tenant_id=None):
        """Return the current total.

        """

    @abc.abstractmethod
    def get_tenants(self, begin=None, end=None):
        """Return the list of rated tenants.

        """

    @abc.abstractmethod
    def get_time_frame(self, begin, end, **filters):
        """Request a time frame from the storage backend.

        :param begin: When to start filtering.
        :type begin: datetime.datetime
        :param end: When to stop filtering.
        :type end: datetime.datetime
        :param res_type: (Optional) Filter on the resource type.
        :type res_type: str
        :param tenant_id: (Optional) Filter on the tenant_id.
        :type res_type: str
        """

    def append(self, raw_data, tenant_id):
        """Append rated data before committing them to the backend.

        :param raw_data: The rated data frames.
        :param tenant_id: Tenant the frame is belonging.
        """
        while raw_data:
            usage_start, data = self._filter_period(raw_data)
            self._check_commit(usage_start, tenant_id)
            self._dispatch(data, tenant_id)
            self._has_data = True

    def nodata(self, begin, end, tenant_id):
        """Append a no data frame to the storage backend.

        :param begin: Begin of the period with no data.
        :param end: End of the period with no data.
        :param tenant_id: Tenant to update with no data marker for the period.
        """
        self._check_commit(begin, tenant_id)

    def commit(self, tenant_id):
        """Commit the changes to the backend.

        """
        self._pre_commit(tenant_id)
        self._commit(tenant_id)
        self._post_commit(tenant_id)
