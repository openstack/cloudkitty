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
import datetime

from ceilometerclient import client as cclient

from cloudkitty import collector


class CeilometerCollector(collector.BaseCollector):
    def __init__(self, **kwargs):
        super(CeilometerCollector, self).__init__(**kwargs)

        self._resource_cache = {}

    def _connect(self):
        """Initialize connection to the Ceilometer endpoint."""
        self._conn = cclient.get_client('2', os_username=self.user,
                                        os_password=self.password,
                                        os_auth_url=self.keystone_url,
                                        os_tenant_name=self.tenant,
                                        os_region_name=self.region)

    def gen_filter(self, op='eq', **kwargs):
        """Generate ceilometer filter from kwargs."""
        q_filter = []
        for kwarg in kwargs:
            q_filter.append({'field': kwarg, 'op': op, 'value': kwargs[kwarg]})
        return q_filter

    def prepend_filter(self, prepend, **kwargs):
        """Filter composer."""
        q_filter = {}
        for kwarg in kwargs:
            q_filter[prepend + kwarg] = kwargs[kwarg]
        return q_filter

    def user_metadata_filter(self, op='eq', **kwargs):
        """Create user_metadata filter from kwargs."""
        user_filter = {}
        for kwarg in kwargs:
            field = kwarg
            # Auto replace of . to _ to match ceilometer behaviour
            if '.' in field:
                field = field.replace('.', '_')
            user_filter[field] = kwargs[kwarg]
        user_filter = self.prepend_filter('user_metadata.', **user_filter)
        return self.metadata_filter(op, **user_filter)

    def metadata_filter(self, op='eq', **kwargs):
        """Create metadata filter from kwargs."""
        meta_filter = self.prepend_filter('metadata.', **kwargs)
        return self.gen_filter(op, **meta_filter)

    def get_active_instances(self, start, end=None, project_id=None,
                             q_filter=None):
        """Instance that were active during the timespan."""
        start_iso = datetime.fromtimestamp(start).isoformat()
        req_filter = self.gen_filter(op='ge', timestamp=start_iso)
        if project_id:
            req_filter.extend(self.gen_filter(project=project_id))
        if end:
            end_iso = datetime.fromtimestamp(end).isoformat()
            req_filter.extend(self.gen_filter(op='le', timestamp=end_iso))
        if isinstance(q_filter, list):
            req_filter.extend(q_filter)
        elif q_filter:
            req_filter.append(q_filter)
        instance_stats = self._conn.statistics.list(meter_name='instance',
                                                    period=0, q=req_filter,
                                                    groupby=['resource_id'])
        return [instance.groupby['resource_id'] for instance in instance_stats]

    def get_compute(self, start, end=None, project_id=None, q_filter=None):
        active_instances = self.get_active_instances(start, end, project_id,
                                                     q_filter)
        compute_data = []
        volume_data = {'unit': 'instance', 'qty': 1}
        for instance in active_instances:
            instance_data = {}
            instance_data['desc'] = self.get_resource_detail(instance)
            instance_data['desc']['instance_id'] = instance
            instance_data['vol'] = volume_data
            compute_data.append(instance_data)

        data = {}
        data['compute'] = compute_data
        return data

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

        res_data['project_id'] = data.project_id
        res_data['user_id'] = data.user_id

        res_data['metadata'] = {}
        for field in data.metadata:
            if field.startswith('user_metadata'):
                res_data['metadata'][field[14:]] = data.metadata[field]

        return res_data

    def strip_resource_data(self, res_data, res_type='compute'):
        if res_type == 'compute':
            return self._strip_compute(res_data)

    def get_resource_detail(self, resource_id):
        if resource_id not in self._resource_cache:
            resource = self._conn.resources.get(resource_id)
            resource = self.strip_resource_data(resource)
            self._resource_cache[resource_id] = resource
        return self._resource_cache[resource_id]
