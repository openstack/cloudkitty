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
    compute_map = {
        'name': ['display_name'],
        'flavor': ['flavor.name', 'instance_type'],
        'vcpus': ['vcpus'],
        'memory': ['memory_mb'],
        'image_id': ['image.id', 'image_meta.base_image_ref'],
        'availability_zone': [
            'availability_zone',
            'OS-EXT-AZ.availability_zone'],
    }

    volume_map = {
        'volume_id': ['volume_id'],
        'name': ['display_name'],
        'availability_zone': ['availability_zone'],
        'size': ['size'],
    }

    image_map = {
        'container_format': ['container_format'],
        'deleted': ['deleted'],
        'disk_format': ['disk_format'],
        'is_public': ['is_public'],
        'name': ['name'],
        'protected': ['protected'],
        'size': ['size'],
        'status': ['status'],
    }

    network_tap_map = {
        'instance_host': ['instance_host'],
        'mac': ['mac'],
        'host': ['host'],
        'vnic_name': ['vnic_name'],
        'instance_id': ['instance_id'],
    }

    network_floating_map = {
        'status': ['status'],
        'router_id': ['router_id'],
        'floating_network_id': ['floating_network_id'],
        'fixed_ip_address': ['fixed_ip_address'],
        'floating_ip_address': ['floating_ip_address'],
        'port_id': ['port_id'],
    }

    radosgw_usage_map = {}

    metadata_item = 'metadata'

    def _strip_compute(self, data):
        res_data = self.generic_strip('compute', data)
        res_data['instance_id'] = data.resource_id
        res_data['project_id'] = data.project_id
        res_data['user_id'] = data.user_id
        res_data['metadata'] = {}
        for field in data.metadata:
            if field.startswith('user_metadata'):
                res_data['metadata'][field[14:]] = data.metadata[field]
        return res_data

    def _strip_volume(self, data):
        res_data = self.generic_strip('volume', data)
        res_data['user_id'] = data.user_id
        res_data['project_id'] = data.project_id
        return res_data

    def _strip_image(self, data):
        res_data = self.generic_strip('image', data)
        res_data['image_id'] = data.resource_id
        res_data['project_id'] = data.project_id
        res_data['user_id'] = data.user_id
        return res_data

    def _strip_network_tap(self, data):
        res_data = self.generic_strip('network_tap', data)
        res_data['user_id'] = data.user_id
        res_data['project_id'] = data.project_id
        res_data['interface_id'] = data.resource_id
        return res_data

    def _strip_network_floating(self, data):
        res_data = self.generic_strip('network_floating', data)
        res_data['user_id'] = data.user_id
        res_data['project_id'] = data.project_id
        res_data['floatingip_id'] = data.resource_id
        return res_data

    def _strip_radosgw_usage(self, data):
        res_data = self.generic_strip('radosgw_usage_size', data)
        res_data['radosgw_id'] = data.resource_id
        res_data['user_id'] = data.user_id
        res_data['project_id'] = data.project_id
        return res_data

    def get_metadata(self, res_type):
        """Return list of metadata available after transformation for given

        resource type.
        """

        class FakeData(dict):
            """FakeData object."""

            def __getattr__(self, name, default=None):
                try:
                    return super(FakeData, self).__getattr__(self, name)
                except AttributeError:
                    return default or name

        # list of metadata is built by applying the generic strip_resource_data
        # function to a fake data object

        fkdt = FakeData()
        setattr(fkdt, self.metadata_item, FakeData())
        res_data = self.strip_resource_data(res_type, fkdt)
        return res_data.keys()
