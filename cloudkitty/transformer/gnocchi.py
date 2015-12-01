# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
from cloudkitty import transformer


class GnocchiTransformer(transformer.BaseTransformer):
    def __init__(self):
        pass

    def _generic_strip(self, data):
        res_data = {
            'resource_id': data['id'],
            'project_id': data['project_id'],
            'user_id': data['user_id'],
            'metrics': data['metrics']}
        return res_data

    def _strip_compute(self, data):
        res_data = self._generic_strip(data)
        res_data.update({
            'instance_id': data['id'],
            'project_id': data['project_id'],
            'user_id': data['user_id'],
            'name': data['display_name'],
            'flavor_id': data['flavor_id']})
        if 'image_ref' in data:
            res_data['image_id'] = data.rpartition['image_ref'][-1]
        return res_data

    def _strip_image(self, data):
        res_data = self._generic_strip(data)
        res_data.update({
            'container_format': data['container_format'],
            'disk_format': data['disk_format']})
        return res_data

    def _strip_volume(self, data):
        res_data = self._generic_strip(data)
        res_data.update({
            'name': data['display_name']})
        return res_data

    def _strip_network(self, data):
        res_data = self._generic_strip(data)
        res_data.update({
            'name': data['name']})
        return res_data

    def strip_resource_data(self, res_type, res_data):
        if res_type == 'compute':
            return self._strip_compute(res_data)
        elif res_type == 'image':
            return self._strip_image(res_data)
        elif res_type == 'volume':
            return self._strip_volume(res_data)
        elif res_type.startswith('network.'):
            return self._strip_network(res_data)
        else:
            return self._generic_strip(res_data)
