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
from gnocchiclient import client as gclient
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

from cloudkitty import collector

GNOCCHI_COLLECTOR_OPTS = 'gnocchi_collector'
ks_loading.register_session_conf_options(
    cfg.CONF,
    GNOCCHI_COLLECTOR_OPTS)
ks_loading.register_auth_conf_options(
    cfg.CONF,
    GNOCCHI_COLLECTOR_OPTS)
CONF = cfg.CONF


class GnocchiCollector(collector.BaseCollector):
    collector_name = 'gnocchi'
    dependencies = ('GnocchiTransformer',
                    'CloudKittyFormatTransformer')
    retrieve_mappings = {
        'compute': 'instance',
        'image': 'image',
        'volume': 'volume',
        'network.bw.out': 'instance_network_interface',
        'network.bw.in': 'instance_network_interface',
    }
    metrics_mappings = {
        'compute': [
            ('vcpus', 'max'),
            ('memory', 'max'),
            ('cpu', 'max'),
            ('disk.root.size', 'max'),
            ('disk.ephemeral.size', 'max')],
        'image': [
            ('image.size', 'max'),
            ('image.download', 'max'),
            ('image.serve', 'max')],
        'volume': [
            ('volume.size', 'max')],
        'network.bw.out': [
            ('network.outgoing.bytes', 'max')],
        'network.bw.in': [
            ('network.incoming.bytes', 'max')],
    }
    volumes_mappings = {
        'compute': (1, 'instance'),
        'image': ('image.size', 'MB'),
        'volume': ('volume.size', 'GB'),
        'network.bw.out': ('network.outgoing.bytes', 'MB'),
        'network.bw.in': ('network.incoming.bytes', 'MB'),
    }

    def __init__(self, transformers, **kwargs):
        super(GnocchiCollector, self).__init__(transformers, **kwargs)

        self.t_gnocchi = self.transformers['GnocchiTransformer']
        self.t_cloudkitty = self.transformers['CloudKittyFormatTransformer']

        self.auth = ks_loading.load_auth_from_conf_options(
            CONF,
            GNOCCHI_COLLECTOR_OPTS)
        self.session = ks_loading.load_session_from_conf_options(
            CONF,
            GNOCCHI_COLLECTOR_OPTS,
            auth=self.auth)
        self._conn = gclient.Client(
            '1',
            session=self.session)

    @classmethod
    def gen_filter(cls, cop='=', lop='and', **kwargs):
        """Generate gnocchi filter from kwargs.

        :param cop: Comparison operator.
        :param lop: Logical operator in case of multiple filters.
        """
        q_filter = []
        for kwarg in sorted(kwargs):
            q_filter.append({cop: {kwarg: kwargs[kwarg]}})
        if len(kwargs) > 1:
            return cls.extend_filter(q_filter, lop=lop)
        else:
            return q_filter[0] if len(kwargs) else {}

    @classmethod
    def extend_filter(cls, *args, **kwargs):
        """Extend an existing gnocchi filter with multiple operations.

        :param lop: Logical operator in case of multiple filters.
        """
        lop = kwargs.get('lop', 'and')
        filter_list = []
        for cur_filter in args:
            if isinstance(cur_filter, dict) and cur_filter:
                filter_list.append(cur_filter)
            elif isinstance(cur_filter, list):
                filter_list.extend(cur_filter)
        if len(filter_list) > 1:
            return {lop: filter_list}
        else:
            return filter_list[0] if len(filter_list) else {}

    def _generate_time_filter(self, start, end=None, with_revision=False):
        """Generate timeframe filter.

        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param with_revision: Filter on the resource revision.
        :type with_revision: bool
        """
        time_filter = list()
        time_filter.append(self.extend_filter(
            self.gen_filter(ended_at=None),
            self.gen_filter(cop=">=", ended_at=start),
            lop='or'))
        if end:
            time_filter.append(self.extend_filter(
                self.gen_filter(ended_at=None),
                self.gen_filter(cop="<=", ended_at=end),
                lop='or'))
            time_filter.append(
                self.gen_filter(cop="<=", started_at=end))
            if with_revision:
                time_filter.append(
                    self.gen_filter(cop="<=", revision_start=end))
        return time_filter

    def _expand_metrics(self, resources, mappings, start, end=None):
        for resource in resources:
            metrics = resource.get('metrics', {})
            for name, aggregate in mappings:
                value = self._conn.metric.get_measures(
                    metric=metrics.get(name),
                    start=start,
                    stop=end,
                    aggregation=aggregate)
                try:
                    resource[name] = value[0][2]
                except IndexError:
                    resource[name] = None

    def resource_info(self,
                      resource_type,
                      start,
                      end=None,
                      resource_id=None,
                      project_id=None,
                      q_filter=None):
        """Get resources during the timeframe.

        Set the resource_id if you want to get a specific resource.
        :param resource_type: Resource type to filter on.
        :type resource_type: str
        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param resource_id: Retrieve a specific resource based on its id.
        :type resource_id: str
        :param project_id: Filter on a specific tenant/project.
        :type project_id: str
        :param q_filter: Append a custom filter.
        :type q_filter: list
        """
        # Translating to resource name if needed
        translated_resource = self.retrieve_mappings.get(resource_type,
                                                         resource_type)
        qty, unit = self.volumes_mappings.get(
            resource_type,
            (1, 'unknown'))
        # NOTE(sheeprine): Only filter revision on resource retrieval
        query_parameters = self._generate_time_filter(
            start,
            end,
            True if resource_id else False)
        need_subquery = True
        if resource_id:
            need_subquery = False
            query_parameters.append(
                self.gen_filter(id=resource_id))
            resources = self._conn.resource.search(
                resource_type=translated_resource,
                query=self.extend_filter(*query_parameters),
                history=True,
                limit=1,
                sorts=['revision_start:desc'])
        else:
            if end:
                query_parameters.append(
                    self.gen_filter(cop="=", type=translated_resource))
            else:
                need_subquery = False
            if project_id:
                query_parameters.append(
                    self.gen_filter(project_id=project_id))
            if q_filter:
                query_parameters.append(q_filter)
            final_query = self.extend_filter(*query_parameters)
            resources = self._conn.resource.search(
                resource_type='generic' if end else translated_resource,
                query=final_query)
        resource_list = list()
        if not need_subquery:
            for resource in resources:
                resource_data = self.t_gnocchi.strip_resource_data(
                    resource_type,
                    resource)
                self._expand_metrics(
                    [resource_data],
                    self.metrics_mappings[resource_type],
                    start,
                    end)
                resource_data.pop('metrics', None)
                data = self.t_cloudkitty.format_item(
                    resource_data,
                    unit,
                    qty if isinstance(qty, int) else resource_data[qty])
                resource_list.append(data)
            return resource_list[0] if resource_id else resource_list
        for resource in resources:
            res = self.resource_info(
                resource_type,
                start,
                end,
                resource_id=resource.get('id', ''))
            resource_list.append(res)
        return resource_list

    def generic_retrieve(self,
                         resource_name,
                         start,
                         end=None,
                         project_id=None,
                         q_filter=None):
        resources = self.resource_info(
            resource_name,
            start,
            end,
            project_id,
            q_filter)
        if not resources:
            raise collector.NoDataCollected(self.collector_name, resource_name)
        for resource in resources:
            # NOTE(sheeprine): Reference to gnocchi resource used by storage
            resource['resource_id'] = resource['desc']['resource_id']
        return self.t_cloudkitty.format_service(resource_name, resources)

    def retrieve(self,
                 resource,
                 start,
                 end=None,
                 project_id=None,
                 q_filter=None):
        trans_resource = resource.replace('_', '.')
        return self.generic_retrieve(
            trans_resource,
            start,
            end,
            project_id,
            q_filter)
