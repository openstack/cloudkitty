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
from stevedore import extension

from cloudkitty import collector
from cloudkitty.db import api as db_api

COLLECTORS_NAMESPACE = 'cloudkitty.collector.backends'


class MetaCollector(collector.BaseCollector):
    def __init__(self, transformers, **kwargs):
        super(MetaCollector, self).__init__(transformers, **kwargs)

        self._db = db_api.get_instance().get_service_to_collector_mapping()

        self._collectors = {}
        self._load_collectors()

        self._mappings = {}
        self._load_mappings()

    def _load_mappings(self):
        mappings = self._db.list_services()
        for mapping in mappings:
            db_mapping = self._db.get_mapping(mapping.service)
            self._mappings[db_mapping.service] = db_mapping.collector

    def _check_enabled(self, name):
        enable_state = db_api.get_instance().get_module_enable_state()
        return enable_state.get_state('collector_{}'.format(name))

    def _load_collectors(self):
        self._collectors = {}
        collectors = extension.ExtensionManager(
            COLLECTORS_NAMESPACE,
        )
        collectors_list = collectors.names()
        collectors_list.remove('meta')

        for name in collectors_list:
            if self._check_enabled(name):
                self._collectors[name] = collectors[name].plugin(
                    self.transformers,
                    period=self.period)

    def map_retrieve(self, trans_resource, res_collector=None):
        if res_collector:
            if hasattr(res_collector, trans_resource):
                return getattr(res_collector, trans_resource)
        for cur_collector in self._collectors.values():
            if hasattr(cur_collector, trans_resource):
                return getattr(cur_collector, trans_resource)

    def retrieve(self, resource, start, end=None, project_id=None,
                 q_filter=None):

        # Resource to function translation
        trans_resource = 'get_'
        trans_resource += resource.replace('.', '_')

        # Resource to collector mapping processing
        res_collector = None
        if resource in self._mappings and resource in self._collectors:
            res_collector = self._collectors[resource]

        func = self.map_retrieve(trans_resource, res_collector)
        if func is not None:
            return func(start, end, project_id, q_filter)
