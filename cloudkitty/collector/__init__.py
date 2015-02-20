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

import cloudkitty.utils as ck_utils


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
            self.period = kwargs['period']
        except IndexError as e:
            raise ValueError("Missing argument (%s)" % e)

        self._check_transformers()

    def _check_transformers(self):
        """Check for transformer prerequisites

        """
        for dependency in self.dependencies:
            if dependency not in self.transformers:
                raise TransformerDependencyError(self.collector_name,
                                                 dependency)

    @staticmethod
    def last_month():
        month_start = ck_utils.get_month_start()
        month_end = ck_utils.get_month_end()
        start_ts = ck_utils.dt2ts(month_start)
        end_ts = ck_utils.dt2ts(month_end)
        return start_ts, end_ts

    @staticmethod
    def current_month():
        month_start = ck_utils.get_month_start()
        return ck_utils.dt2ts(month_start)

    def retrieve(self, resource, start, end=None, project_id=None,
                 q_filter=None):
        trans_resource = 'get_'
        trans_resource += resource.replace('.', '_')
        if not hasattr(self, trans_resource):
            return None
        func = getattr(self, trans_resource)
        return func(start, end, project_id, q_filter)
