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
import pecan
from pecan import routing
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from cloudkitty import billing
from cloudkitty.billing.hash.db import api
from cloudkitty.db import api as db_api
from cloudkitty.openstack.common import log as logging


LOG = logging.getLogger(__name__)

MAP_TYPE = wtypes.Enum(wtypes.text, 'flat', 'rate')


class Mapping(wtypes.Base):

    map_type = wtypes.wsattr(MAP_TYPE, default='rate', name='type')

    value = wtypes.wsattr(float, mandatory=True)


class BasicHashMapConfigController(billing.BillingConfigController):

    @pecan.expose()
    def _route(self, args, request=None):
        if len(args) > 2:
            # Taken from base _route function
            if request is None:
                from pecan import request  # noqa
            method = request.params.get('_method', request.method).lower()
            if request.method == 'GET' and method in ('delete', 'put'):
                pecan.abort(405)

            if request.method == 'GET':
                return routing.lookup_controller(self.get_mapping, args)
        return super(BasicHashMapConfigController, self)._route(args)

    @wsme_pecan.wsexpose(Mapping, wtypes.text, wtypes.text, wtypes.text)
    def get_mapping(self, service, field, key):
        """Return the list of every mappings.

        """
        hashmap = api.get_instance()
        try:
            return hashmap.get_mapping(service, field, key)
        except (api.NoSuchService, api.NoSuchField, api.NoSuchMapping) as e:
                pecan.abort(400, str(e))

    @wsme_pecan.wsexpose([wtypes.text])
    def get(self):
        hashmap = api.get_instance()
        return [service.name for service in hashmap.list_services()]

    @wsme_pecan.wsexpose([wtypes.text], wtypes.text, wtypes.text)
    def get_one(self, service=None, field=None):
        """Return the list of every sub keys.

        """
        hashmap = api.get_instance()
        if field:
            try:
                return [mapping.key for mapping in hashmap.list_mappings(
                    service,
                    field)]
            except (api.NoSuchService, api.NoSuchField) as e:
                pecan.abort(400, str(e))

        else:
            try:
                return [f.name for f in hashmap.list_fields(service)]
            except api.NoSuchService as e:
                pecan.abort(400, str(e))

    # FIXME (sheeprine): Still a problem with our routing and the different
    # object types. For service/field it's text or a mapping.
    @wsme_pecan.wsexpose(None, wtypes.text, wtypes.text, wtypes.text,
                         body=Mapping)
    def post(self, service, field=None, key=None, mapping=None):
        hashmap = api.get_instance()
        if field:
            if key:
                if mapping:
                    try:
                        # FIXME(sheeprine): We should return the result
                        hashmap.create_mapping(
                            service,
                            field,
                            key,
                            value=mapping.value,
                            map_type=mapping.map_type
                        )
                        pecan.response.headers['Location'] = pecan.request.path
                    except api.MappingAlreadyExists as e:
                        pecan.abort(409, str(e))
                else:
                    e = ValueError('Mapping can\'t be empty.')
                    pecan.abort(400, str(e))
            else:
                try:
                    hashmap.create_field(service, field)
                    pecan.response.headers['Location'] = pecan.request.path
                except api.FieldAlreadyExists as e:
                    pecan.abort(409, str(e))
        else:
            try:
                hashmap.create_service(service)
                pecan.response.headers['Location'] = pecan.request.path
            except api.ServiceAlreadyExists as e:
                pecan.abort(409, str(e))
        pecan.response.status = 201

    @wsme_pecan.wsexpose(None, wtypes.text, wtypes.text, wtypes.text,
                         body=Mapping)
    def put(self, service, field, key, mapping):
        hashmap = api.get_instance()
        try:
            hashmap.update_mapping(
                service,
                field,
                key,
                value=mapping.value,
                map_type=mapping.map_type
            )
            pecan.response.headers['Location'] = pecan.request.path
            pecan.response.status = 204
        except (api.NoSuchService, api.NoSuchField, api.NoSuchMapping) as e:
            pecan.abort(400, str(e))

    @wsme_pecan.wsexpose(None, wtypes.text, wtypes.text, wtypes.text)
    def delete(self, service, field=None, key=None):
        """Delete the parent and all the sub keys recursively.

        """
        hashmap = api.get_instance()
        try:
            if field:
                if key:
                    hashmap.delete_mapping(service, field, key)
                else:
                    hashmap.delete_field(service, field)
            else:
                hashmap.delete_service(service)
        except (api.NoSuchService, api.NoSuchField, api.NoSuchMapping) as e:
            pecan.abort(400, str(e))
        pecan.response.status = 204


class BasicHashMapController(billing.BillingController):

    _custom_actions = {
        'types': ['GET']
    }

    config = BasicHashMapConfigController()

    def get_module_info(self):
        module = BasicHashMap()
        infos = {
            'name': 'hashmap',
            'description': 'Basic hashmap billing module.',
            'enabled': module.enabled,
            'hot_config': True,
        }
        return infos

    @wsme_pecan.wsexpose([wtypes.text])
    def get_types(self):
        """Return the list of every mapping type available.

        """
        return MAP_TYPE.values


class BasicHashMap(billing.BillingProcessorBase):

    controller = BasicHashMapController
    db_api = api.get_instance()

    def __init__(self):
        self._billing_info = {}
        self._load_billing_rates()

    @property
    def enabled(self):
        """Check if the module is enabled

        :returns: bool if module is enabled
        """
        # FIXME(sheeprine): Hardcoded values to check the state
        api = db_api.get_instance()
        module_db = api.get_module_enable_state()
        return module_db.get_state('hashmap') or False

    def reload_config(self):
        self._load_billing_rates()

    def _load_billing_rates(self):
        self._billing_info = {}
        hashmap = api.get_instance()
        services = hashmap.list_services()
        for service in services:
            service = service[0]
            self._billing_info[service] = {}
            fields = hashmap.list_fields(service)
            for field in fields:
                field = field[0]
                self._billing_info[service][field] = {}
                mappings = hashmap.list_mappings(service, field)
                for mapping in mappings:
                    mapping = mapping[0]
                    mapping_db = hashmap.get_mapping(service, field, mapping)
                    map_dict = {}
                    map_dict['value'] = mapping_db.value
                    map_dict['type'] = mapping_db.map_type
                    self._billing_info[service][field][mapping] = map_dict

    def process_service(self, name, data):
        if name not in self._billing_info:
            return
        serv_b_info = self._billing_info[name]
        for entry in data:
            flat = 0
            rate = 1
            entry_desc = entry['desc']
            for field in serv_b_info:
                if field not in entry_desc:
                    continue
                b_info = serv_b_info[field]
                key = entry_desc[field]

                value = 0
                if key in b_info:
                    value = b_info[key]['value']
                elif '_DEFAULT_' in b_info:
                    value = b_info['_DEFAULT_']

                if value:
                    if b_info[key]['type'] == 'rate':
                        rate *= value
                    elif b_info[key]['type'] == 'flat':
                        new_flat = 0
                        new_flat = value
                        if new_flat > flat:
                            flat = new_flat
            entry['billing'] = {'price': flat * rate}

    def process(self, data):
        for cur_data in data:
            cur_usage = cur_data['usage']
            for service in cur_usage:
                self.process_service(service, cur_usage[service])
        return data
