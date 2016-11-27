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
import decimal

from cloudkitty import rating
from cloudkitty.rating.hash.controllers import root as root_api
from cloudkitty.rating.hash.db import api as hash_db_api


class HashMap(rating.RatingProcessorBase):
    """HashMap rating module.

    HashMap can be used to map arbitrary fields of a resource to different
    costs.
    """

    module_name = 'hashmap'
    description = 'HashMap rating module.'
    hot_config = True
    config_controller = root_api.HashMapConfigController

    db_api = hash_db_api.get_instance()

    def __init__(self, tenant_id=None):
        super(HashMap, self).__init__(tenant_id)
        self._entries = {}
        self._res = {}
        self._load_rates()

    def reload_config(self):
        """Reload the module's configuration.

        """
        self._load_rates()

    def _load_mappings(self, mappings_uuid_list):
        hashmap = hash_db_api.get_instance()
        mappings = {}
        for mapping_uuid in mappings_uuid_list:
            mapping_db = hashmap.get_mapping(uuid=mapping_uuid)
            if mapping_db.group_id:
                group_name = mapping_db.group.name
            else:
                group_name = '_DEFAULT_'
            if group_name not in mappings:
                mappings[group_name] = {}
            current_scope = mappings[group_name]

            mapping_value = mapping_db.value
            if mapping_value:
                current_scope[mapping_value] = {}
                current_scope = current_scope[mapping_value]
            current_scope['type'] = mapping_db.map_type
            current_scope['cost'] = mapping_db.cost
        return mappings

    def _load_thresholds(self, thresholds_uuid_list):
        hashmap = hash_db_api.get_instance()
        thresholds = {}
        for threshold_uuid in thresholds_uuid_list:
            threshold_db = hashmap.get_threshold(uuid=threshold_uuid)
            if threshold_db.group_id:
                group_name = threshold_db.group.name
            else:
                group_name = '_DEFAULT_'
            if group_name not in thresholds:
                thresholds[group_name] = {}
            current_scope = thresholds[group_name]

            threshold_level = threshold_db.level
            current_scope[threshold_level] = {}
            current_scope = current_scope[threshold_level]
            current_scope['type'] = threshold_db.map_type
            current_scope['cost'] = threshold_db.cost
        return thresholds

    def _update_entries(self,
                        entry_type,
                        root,
                        service_uuid=None,
                        field_uuid=None,
                        tenant_uuid=None):
        hashmap = hash_db_api.get_instance()
        list_func = getattr(hashmap, 'list_{}'.format(entry_type))
        entries_uuid_list = list_func(
            service_uuid=service_uuid,
            field_uuid=field_uuid,
            tenant_uuid=tenant_uuid)
        load_func = getattr(self, '_load_{}'.format(entry_type))
        entries = load_func(entries_uuid_list)
        if entry_type in root:
            res = root[entry_type]
            for group, values in entries.items():
                if group in res:
                    res[group].update(values)
                else:
                    res[group] = values
        else:
            root[entry_type] = entries

    def _load_service_entries(self, service_name, service_uuid):
        self._entries[service_name] = dict()
        for entry_type in ('mappings', 'thresholds'):
            for tenant in (None, self._tenant_id):
                self._update_entries(
                    entry_type,
                    self._entries[service_name],
                    service_uuid=service_uuid,
                    tenant_uuid=tenant)

    def _load_field_entries(self, service_name, field_name, field_uuid):
        if service_name not in self._entries:
            self._entries[service_name] = {}
        if 'fields' not in self._entries[service_name]:
            self._entries[service_name]['fields'] = {}
        scope = self._entries[service_name]['fields'][field_name] = {}
        for entry_type in ('mappings', 'thresholds'):
            for tenant in (None, self._tenant_id):
                self._update_entries(
                    entry_type,
                    scope,
                    field_uuid=field_uuid,
                    tenant_uuid=tenant)

    def _load_rates(self):
        self._entries = {}
        hashmap = hash_db_api.get_instance()
        services_uuid_list = hashmap.list_services()
        for service_uuid in services_uuid_list:
            service_db = hashmap.get_service(uuid=service_uuid)
            service_name = service_db.name
            self._load_service_entries(service_name, service_uuid)
            fields_uuid_list = hashmap.list_fields(service_uuid)
            for field_uuid in fields_uuid_list:
                field_db = hashmap.get_field(uuid=field_uuid)
                field_name = field_db.name
                self._load_field_entries(service_name, field_name, field_uuid)

    def add_rating_informations(self, data):
        if 'rating' not in data:
            data['rating'] = {'price': 0}
        for entry in self._res.values():
            rate = entry['rate']
            flat = entry['flat']
            if entry['threshold']['scope'] == 'field':
                if entry['threshold']['type'] == 'flat':
                    flat += entry['threshold']['cost']
                else:
                    rate *= entry['threshold']['cost']
            res = rate * flat
            # FIXME(sheeprine): Added here to ensure that qty is decimal
            res *= decimal.Decimal(data['vol']['qty'])
            if entry['threshold']['scope'] == 'service':
                if entry['threshold']['type'] == 'flat':
                    res += entry['threshold']['cost']
                else:
                    res *= entry['threshold']['cost']
            data['rating']['price'] += res

    def update_result(self,
                      group,
                      map_type,
                      cost,
                      level=0,
                      is_threshold=False,
                      threshold_scope='field'):
        if group not in self._res:
            self._res[group] = {'flat': 0,
                                'rate': 1,
                                'threshold': {
                                    'level': -1,
                                    'cost': 0,
                                    'type': 'flat',
                                    'scope': 'field'}}
        if is_threshold:
            best = self._res[group]['threshold']['level']
            if level > best:
                self._res[group]['threshold']['level'] = level
                self._res[group]['threshold']['cost'] = cost
                self._res[group]['threshold']['type'] = map_type
                self._res[group]['threshold']['scope'] = threshold_scope
        else:
            if map_type == 'rate':
                self._res[group]['rate'] *= cost
            elif map_type == 'flat':
                new_flat = cost
                cur_flat = self._res[group]['flat']
                if new_flat > cur_flat:
                    self._res[group]['flat'] = new_flat

    def process_mappings(self,
                         mapping_groups,
                         cmp_value):
        for group_name, mappings in mapping_groups.items():
            for mapping_value, mapping in mappings.items():
                if cmp_value == mapping_value:
                    self.update_result(
                        group_name,
                        mapping['type'],
                        mapping['cost'])

    def process_thresholds(self,
                           threshold_groups,
                           cmp_level,
                           threshold_type):
        for group_name, thresholds in threshold_groups.items():
            for threshold_level, threshold in thresholds.items():
                if cmp_level >= threshold_level:
                    self.update_result(
                        group_name,
                        threshold['type'],
                        threshold['cost'],
                        threshold_level,
                        True,
                        threshold_type)

    def process_services(self, service_name, data):
        if service_name not in self._entries:
            return
        service_mappings = self._entries[service_name]['mappings']
        for group_name, mapping in service_mappings.items():
            self.update_result(group_name,
                               mapping['type'],
                               mapping['cost'])
        service_thresholds = self._entries[service_name]['thresholds']
        self.process_thresholds(service_thresholds,
                                data['vol']['qty'],
                                'service')

    def process_fields(self, service_name, data):
        if service_name not in self._entries:
            return
        if 'fields' not in self._entries[service_name]:
            return
        desc_data = data['desc']
        field_mappings = self._entries[service_name]['fields']
        for field_name, group_mappings in field_mappings.items():
            if field_name not in desc_data:
                continue
            cmp_value = desc_data[field_name]
            self.process_mappings(group_mappings['mappings'],
                                  cmp_value)
            if group_mappings['thresholds']:
                self.process_thresholds(group_mappings['thresholds'],
                                        decimal.Decimal(cmp_value),
                                        'field')

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service_name, service_data in cur_usage.items():
                for item in service_data:
                    self._res = {}
                    self.process_services(service_name, item)
                    self.process_fields(service_name, item)
                    self.add_rating_informations(item)
        return data
