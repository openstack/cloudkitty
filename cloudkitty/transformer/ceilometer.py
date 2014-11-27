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
from cloudkitty import transformer


class CeilometerTransformer(transformer.BaseTransformer):
    def __init__(self):
        pass

    def _strip_compute(self, data):
        res_data = {}
        res_data['name'] = data.metadata.get('display_name')
        res_data['flavor'] = data.metadata.get('flavor.name')
        res_data['vcpus'] = data.metadata.get('vcpus')
        res_data['memory'] = data.metadata.get('memory_mb')
        res_data['image_id'] = data.metadata.get('image.id')
        res_data['availability_zone'] = (
            data.metadata.get('OS-EXT-AZ.availability_zone')
        )

        res_data['instance_id'] = data.resource_id
        res_data['project_id'] = data.project_id
        res_data['user_id'] = data.user_id

        res_data['metadata'] = {}
        for field in data.metadata:
            if field.startswith('user_metadata'):
                res_data['metadata'][field[14:]] = data.metadata[field]

        return res_data

    def strip_resource_data(self, res_type, res_data):
        if res_type == 'compute':
            return self._strip_compute(res_data)
        elif res_type == 'image':
            return res_data.metadata
