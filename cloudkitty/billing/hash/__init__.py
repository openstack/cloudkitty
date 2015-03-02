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
from cloudkitty import billing
from cloudkitty.billing.hash.controllers import root as root_api
from cloudkitty.billing.hash.db import api as hash_db_api
from cloudkitty.db import api as ck_db_api
from cloudkitty.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class HashMap(billing.BillingProcessorBase):
    """HashMap rating module.

    HashMap can be used to map arbitrary fields of a resource to different
    costs.
    """

    module_name = 'hashmap'
    description = 'Basic hashmap billing module.'
    hot_config = True
    config_controller = root_api.HashMapConfigController

    db_api = hash_db_api.get_instance()

    def __init__(self, tenant_id=None):
        super(HashMap, self).__init__(tenant_id)
        self._service_mappings = {}
        self._field_mappings = {}
        self._res = {}
        self._load_billing_rates()

    @property
    def enabled(self):
        """Check if the module is enabled

        :returns: bool if module is enabled
        """
        db_api = ck_db_api.get_instance()
        module_db = db_api.get_module_enable_state()
        return module_db.get_state('hashmap') or False

    def reload_config(self):
        """Reload the module's configuration.

        """
        self._load_billing_rates()

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
            mapping_value = mapping_db.value
            map_dict = {}
            map_dict['cost'] = mapping_db.cost
            map_dict['type'] = mapping_db.map_type
            if mapping_value:
                mappings[group_name][mapping_value] = map_dict
            else:
                mappings[group_name] = map_dict
        return mappings

    def _load_service_mappings(self, service_name, service_uuid):
        hashmap = hash_db_api.get_instance()
        mappings_uuid_list = hashmap.list_mappings(service_uuid=service_uuid)
        mappings = self._load_mappings(mappings_uuid_list)
        if mappings:
            self._service_mappings[service_name] = mappings

    def _load_field_mappings(self, service_name, field_name, field_uuid):
        hashmap = hash_db_api.get_instance()
        mappings_uuid_list = hashmap.list_mappings(field_uuid=field_uuid)
        mappings = self._load_mappings(mappings_uuid_list)
        if mappings:
            self._field_mappings[service_name] = {}
            self._field_mappings[service_name][field_name] = mappings

    def _load_billing_rates(self):
        self._service_mappings = {}
        self._field_mappings = {}
        hashmap = hash_db_api.get_instance()
        services_uuid_list = hashmap.list_services()
        for service_uuid in services_uuid_list:
            service_db = hashmap.get_service(uuid=service_uuid)
            service_name = service_db.name
            self._load_service_mappings(service_name, service_uuid)
            fields_uuid_list = hashmap.list_fields(service_uuid)
            for field_uuid in fields_uuid_list:
                field_db = hashmap.get_field(uuid=field_uuid)
                field_name = field_db.name
                self._load_field_mappings(service_name, field_name, field_uuid)

    def add_billing_informations(self, data):
        if 'billing' not in data:
            data['billing'] = {'price': 0}
        for entry in self._res.values():
            res = entry['rate'] * entry['flat']
            data['billing']['price'] += res * data['vol']['qty']

    def update_result(self, group, map_type, value):
        if group not in self._res:
            self._res[group] = {'flat': 0,
                                'rate': 1}

        if map_type == 'rate':
            self._res[group]['rate'] *= value
        elif map_type == 'flat':
            new_flat = value
            cur_flat = self._res[group]['flat']
            if new_flat > cur_flat:
                self._res[group]['flat'] = new_flat

    def process_service_map(self, service_name, data):
        if service_name not in self._service_mappings:
            return
        serv_map = self._service_mappings[service_name]
        for group_name, mapping in serv_map.items():
            self.update_result(group_name,
                               mapping['type'],
                               mapping['cost'])

    def process_field_map(self, service_name, data):
        if service_name not in self._field_mappings:
            return {}
        field_map = self._field_mappings[service_name]
        desc_data = data['desc']
        for field_name, group_mappings in field_map.items():
            if field_name not in desc_data:
                continue
            for group_name, mappings in group_mappings.items():
                mapping_default = mappings.pop('_DEFAULT_', {})
                matched = False
                for mapping_value, mapping in mappings.items():
                    if desc_data[field_name] == mapping_value:
                        self.update_result(
                            group_name,
                            mapping['type'],
                            mapping['cost'])
                        matched = True
                if not matched and mapping_default:
                    self.update_result(
                        group_name,
                        mapping_default['type'],
                        mapping_default['cost'])

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service_name, service_data in cur_usage.items():
                for item in service_data:
                    self._res = {}
                    self.process_service_map(service_name, item)
                    self.process_field_map(service_name, item)
                    self.add_billing_informations(item)
        return data
