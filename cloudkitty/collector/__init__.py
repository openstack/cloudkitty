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

import six

import cloudkitty.utils as utils


class TransformerDependencyError(Exception):
    """Raised when a collector can't find a mandatory transformer."""

    def __init__(self, collector, transformer):
        super(TransformerDependencyError, self).__init__(
            "Transformer '%s' not found, but required by %s" % (transformer,
                                                                collector))
        self.collector = collector
        self.transformer = transformer


@six.add_metaclass(abc.ABCMeta)
class BaseCollector(object):
    dependencies = []

    def __init__(self, transformers, **kwargs):
        try:
            self.transformers = transformers
            self.user = kwargs['user']
            self.password = kwargs['password']
            self.tenant = kwargs['tenant']
            self.region = kwargs['region']
            self.keystone_url = kwargs['keystone_url']
            self.period = kwargs['period']
        except IndexError as e:
            raise ValueError("Missing argument (%s)" % e)

        self._check_transformers()

        self._conn = None
        self._connect()

    def _check_transformers(self):
        """Check for transformer prerequisites

        """
        for dependency in self.dependencies:
            if dependency not in self.transformers:
                raise TransformerDependencyError(self.collector_name,
                                                 dependency)

    @abc.abstractmethod
    def _connect(self):
        """Connect to the backend

        """

    @staticmethod
    def last_month():
        now = datetime.datetime.now()
        month_end = (datetime.datetime(now.year, now.month, 1) -
                     datetime.timedelta(days=1))
        month_start = month_end.replace(day=1)
        start_ts = utils.dt2ts(month_start)
        end_ts = utils.dt2ts(month_end)
        return start_ts, end_ts

    @staticmethod
    def current_month():
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        return utils.dt2ts(month_start)

    def retrieve(self, resource, start, end=None, project_id=None,
                 q_filter=None):
        trans_resource = 'get_'
        trans_resource += resource.replace('.', '_')
        if not hasattr(self, trans_resource):
            return None
        func = getattr(self, trans_resource)
        return func(start, end, project_id, q_filter)
