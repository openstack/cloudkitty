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
import decimal

from gnocchiclient import client as gclient
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import units

from cloudkitty import collector
from cloudkitty import utils as ck_utils


LOG = logging.getLogger(__name__)

GNOCCHI_COLLECTOR_OPTS = 'gnocchi_collector'
gnocchi_collector_opts = ks_loading.get_auth_common_conf_options()

cfg.CONF.register_opts(gnocchi_collector_opts, GNOCCHI_COLLECTOR_OPTS)
ks_loading.register_session_conf_options(
    cfg.CONF,
    GNOCCHI_COLLECTOR_OPTS)
ks_loading.register_auth_conf_options(
    cfg.CONF,
    GNOCCHI_COLLECTOR_OPTS)
CONF = cfg.CONF

METRICS_CONF = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)


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
        'network.floating': 'network',
        'radosgw.usage': 'ceph_account',
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
        'network.floating': [
            ('ip.floating', 'max')],
        'radosgw.usage': [
            ('radosgw.objects.size', 'max')],
    }
    units_mappings = {
        'compute': (1, 'instance'),
        'image': ('image.size', 'MiB'),
        'volume': ('volume.size', 'GiB'),
        'network.bw.out': ('network.outgoing.bytes', 'MB'),
        'network.bw.in': ('network.incoming.bytes', 'MB'),
        'network.floating': (1, 'ip'),
        'radosgw.usage': ('radosgw.objects.size', 'GiB')
    }
    default_unit = (1, 'unknown')

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
    def get_metadata(cls, resource_name, transformers):
        info = super(GnocchiCollector, cls).get_metadata(resource_name,
                                                         transformers)
        try:
            info["metadata"].extend(transformers['GnocchiTransformer']
                                    .get_metadata(resource_name))

            try:
                tmp = METRICS_CONF['metrics_units'][resource_name]
                info['unit'] = list(tmp.values())[0]['unit']
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                info['unit'] = cls.units_mappings[resource_name][1]

        except KeyError:
            pass
        return info

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

    def _generate_time_filter(self, start, end):
        """Generate timeframe filter.

        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        """
        time_filter = list()
        time_filter.append(self.extend_filter(
            self.gen_filter(ended_at=None),
            self.gen_filter(cop=">=", ended_at=start),
            lop='or'))
        time_filter.append(
            self.gen_filter(cop="<=", started_at=end))
        return time_filter

    def _expand(self, metrics, resource, name, aggregate, start, end):
        try:
            values = self._conn.metric.get_measures(
                metric=metrics[name],
                start=ck_utils.ts2dt(start),
                stop=ck_utils.ts2dt(end),
                aggregation=aggregate)
            # NOTE(sheeprine): Get the list of values for the current
            # metric and get the first result value.
            # [point_date, granularity, value]
            # ["2015-11-24T00:00:00+00:00", 86400.0, 64.0]
            resource[name] = values[0][2]
        except IndexError:
            resource[name] = 0
        except KeyError:
            # Skip metrics not found
            pass

    def _expand_metrics(self, resources, mappings, start, end):
        for resource in resources:
            metrics = resource.get('metrics', {})
            try:
                for mapping in mappings:
                    self._expand(
                        metrics,
                        resource,
                        mapping.keys()[0],
                        mapping.values()[0],
                        start,
                        end,
                    )
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except AttributeError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                for name, aggregate in mappings:
                    self._expand(
                        metrics,
                        resource,
                        name,
                        aggregate,
                        start,
                        end,
                    )

    def get_resources(self, resource_name, start, end,
                      project_id, q_filter=None):
        """Get resources during the timeframe.

        :param resource_name: Resource name to filter on.
        :type resource_name: str
        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param project_id: Filter on a specific tenant/project.
        :type project_id: str
        :param q_filter: Append a custom filter.
        :type q_filter: list
        """
        # NOTE(sheeprine): We first get the list of every resource running
        # without any details or history.
        # Then we get information about the resource getting details and
        # history.

        # Translating the resource name if needed
        query_parameters = self._generate_time_filter(start, end)

        try:
            resource_type = METRICS_CONF['services_objects'].get(resource_name)
        # NOTE(mc): deprecated except part kept for backward compatibility.
        except KeyError:
            LOG.warning('Error when trying to use yaml metrology conf.')
            LOG.warning('Fallback on the deprecated oslo config method.')
            resource_type = self.retrieve_mappings.get(resource_name)

        query_parameters.append(
            self.gen_filter(cop="=", type=resource_type))
        query_parameters.append(
            self.gen_filter(project_id=project_id))
        if q_filter:
            query_parameters.append(q_filter)
        resources = self._conn.resource.search(
            resource_type=resource_type,
            query=self.extend_filter(*query_parameters))
        return resources

    def resource_info(self, resource_name, start, end, project_id,
                      q_filter=None):
        try:
            tmp = METRICS_CONF['metrics_units'][resource_name]
            qty = list(tmp.keys())[0]
            unit = list(tmp.values())[0]['unit']
        # NOTE(mc): deprecated except part kept for backward compatibility.
        except KeyError:
            LOG.warning('Error when trying to use yaml metrology conf.')
            LOG.warning('Fallback on the deprecated oslo config method.')
            qty, unit = self.units_mappings.get(
                resource_name,
                self.default_unit,
            )

        resources = self.get_resources(resource_name, start, end,
                                       project_id=project_id,
                                       q_filter=q_filter)
        formated_resources = list()
        for resource in resources:
            resource_data = self.t_gnocchi.strip_resource_data(
                resource_name, resource)

            try:
                mappings = METRICS_CONF['services_metrics'][resource_name]
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated oslo config method.')
                mappings = self.metrics_mappings[resource_name]

            self._expand_metrics([resource_data], mappings, start, end)
            resource_data.pop('metrics', None)

            # Unit conversion
            try:
                conv_data = METRICS_CONF['metrics_units'][resource_name][qty]
                if isinstance(qty, str):
                    resource_data[qty] = ck_utils.convert_unit(
                        resource_data[qty],
                        conv_data.get('factor', 1),
                        conv_data.get('offset', 0),
                    )
            # NOTE(mc): deprecated except part kept for backward compatibility.
            except KeyError:
                LOG.warning('Error when trying to use yaml metrology conf.')
                LOG.warning('Fallback on the deprecated hardcoded method.')

                if resource.get('type') == 'instance_network_interface':
                    resource_data[qty] = (
                        decimal.Decimal(resource_data[qty]) / units.M
                    )
                elif resource.get('type') == 'image':
                    resource_data[qty] = (
                        decimal.Decimal(resource_data[qty]) / units.Mi
                    )
                elif resource.get('type') == 'ceph_account':
                    resource_data[qty] = (
                        decimal.Decimal(resource_data[qty]) / units.Gi)

            data = self.t_cloudkitty.format_item(
                resource_data,
                unit,
                decimal.Decimal(
                    qty if isinstance(qty, int) else resource_data[qty]
                )
            )

            # NOTE(sheeprine): Reference to gnocchi resource used by storage
            data['resource_id'] = data['desc']['resource_id']
            formated_resources.append(data)
        return formated_resources

    def retrieve(self, resource_name, start, end, project_id, q_filter=None):
        resources = self.resource_info(resource_name, start, end,
                                       project_id=project_id,
                                       q_filter=q_filter)
        if not resources:
            raise collector.NoDataCollected(self.collector_name, resource_name)
        return self.t_cloudkitty.format_service(resource_name, resources)
