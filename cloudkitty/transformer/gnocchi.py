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
    compute_map = {
        'instance_id': ['id'],
        'name': ['display_name'],
        'flavor_id': ['flavor_id'],
        'image_id': lambda x, y: x.get_image_id(y),
    }
    image_map = {
        'container_format': ['container_format'],
        'disk_format': ['disk_format'],
    }
    volume_map = {
        'name': ['display_name'],
        'volume_type': ['volume_type'],
    }
    network_map = {
        'name': ['name'],
    }

    def _generic_strip(self, data):
        res_data = {
            'resource_id': data['id'],
            'project_id': data['project_id'],
            'user_id': data['user_id'],
            'metrics': data['metrics']}
        return res_data

    @staticmethod
    def get_image_id(data):
        image_ref = data.get('image_ref', None)
        return image_ref.rpartition('/')[-1] if image_ref else None

    def strip_resource_data(self, res_type, res_data):
        result = self._generic_strip(res_data)
        stripped_data = super(GnocchiTransformer, self).strip_resource_data(
            res_type,
            res_data)
        result.update(stripped_data)
        return result

    def get_metadata(self, res_type):
        """Return list of metadata available after transformation for

        given resource type.
        """

        class FakeData(dict):
            """FakeData object."""

            def __getitem__(self, item):
                try:
                    return super(FakeData, self).__getitem__(item)
                except KeyError:
                    return item

            def get(self, item, default=None):
                return super(FakeData, self).get(item, item)

        # list of metadata is built by applying the generic strip_resource_data
        # function to a fake data object

        fkdt = FakeData()
        res_data = self.strip_resource_data(res_type, fkdt)
        return res_data.keys()
