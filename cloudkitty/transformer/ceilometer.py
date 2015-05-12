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
import six

from cloudkitty import transformer


class CeilometerTransformer(transformer.BaseTransformer):
    def __init__(self):
        pass

    def _strip_compute(self, data):
        metadata_map = {
            'name': ['display_name'],
            'flavor': ['flavor.name', 'instance_type'],
            'vcpus': ['vcpus'],
            'memory': ['memory_mb'],
            'image_id': ['image.id', 'image_meta.base_image_ref'],
            'availability_zone': ['availability_zone',
                                  'OS-EXT-AZ.availability_zone'],
        }

        res_data = {}
        res_data['instance_id'] = data.resource_id
        res_data['project_id'] = data.project_id
        res_data['user_id'] = data.user_id

        for key, meta_keys in six.iteritems(metadata_map):
            for meta_key in meta_keys:
                if key not in res_data or res_data[key] is None:
                    res_data[key] = data.metadata.get(meta_key)

        res_data['metadata'] = {}
        for field in data.metadata:
            if field.startswith('user_metadata'):
                res_data['metadata'][field[14:]] = data.metadata[field]

        return res_data

    def _strip_volume(self, data):
        res_data = {}
        res_data['user_id'] = data.user_id
        res_data['project_id'] = data.project_id
        res_data['volume_id'] = data.metadata['volume_id']
        res_data['availability_zone'] = data.metadata['availability_zone']
        res_data['size'] = data.metadata['size']
        return res_data

    def strip_resource_data(self, res_type, res_data):
        if res_type == 'compute':
            return self._strip_compute(res_data)
        elif res_type == 'volume':
            return self._strip_volume(res_data)
        else:
            return res_data.metadata
