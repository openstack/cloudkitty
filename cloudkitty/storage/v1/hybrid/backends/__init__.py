# -*- coding: utf-8 -*-
# Copyright 2017 Objectif Libre
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
# @author: Luka Peschke
#
import abc

import six


@six.add_metaclass(abc.ABCMeta)
class BaseHybridBackend(object):
    """Base Backend class for the Hybrid Storage.

    This is the interface that all backends for the hybrid storage
    should implement.
    """

    @abc.abstractmethod
    def commit(self, tenant_id, state):
        """Push data to the storage backend.

        :param tenant_id: id of the tenant which information must be committed.
        """
        pass

    @abc.abstractmethod
    def init(self):
        """Initialize hybrid storage backend.

        Can be used to create DB scheme on first start
        """
        pass

    @abc.abstractmethod
    def get_total(self, begin=None, end=None, tenant_id=None,
                  service=None, groupby=None):
        """Return the current total.

        :param begin: When to start filtering.
        :type begin: datetime.datetime
        :param end: When to stop filtering.
        :type end: datetime.datetime
        :param tenant_id: Filter on the tenant_id.
        :type res_type: str
        :param service: Filter on the resource type.
        :type service: str
        :param groupby: Fields to group by, separated by commas if multiple.
        :type groupby: str
        """
        pass

    @abc.abstractmethod
    def append_time_frame(self, res_type, frame, tenant_id):
        """Append a time frame to commit to the backend.

        :param res_type: The resource type of the dataframe.
        :param frame: The timeframe to append.
        :param tenant_id: Tenant the frame is belonging to.
        """
        pass

    @abc.abstractmethod
    def get_tenants(self, begin, end):
        """Return the list of rated tenants.

        :param begin: When to start filtering.
        :type begin: datetime.datetime
        :param end: When to stop filtering.
        :type end: datetime.datetime
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
