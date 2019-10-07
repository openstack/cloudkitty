# -*- coding: utf-8 -*-
# Copyright 2017 Objectif Libre
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
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging
from voluptuous import All
from voluptuous import In
from voluptuous import Length
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import collector
from cloudkitty.common import monasca_client as mon_client_utils
from cloudkitty import dataframe
from cloudkitty import utils as ck_utils

LOG = logging.getLogger(__name__)

MONASCA_API_VERSION = '2_0'
COLLECTOR_MONASCA_OPTS = 'collector_monasca'

collector_monasca_opts = [
    cfg.StrOpt(
        'interface',
        default='internal',
        help='Endpoint URL type (defaults to internal)',
    ),
    cfg.StrOpt(
        'monasca_service_name',
        default='monasca',
        help='Name of the Monasca service (defaults to monasca)',
    ),
]

CONF = cfg.CONF

CONF.register_opts(collector_monasca_opts, COLLECTOR_MONASCA_OPTS)
ks_loading.register_auth_conf_options(CONF, COLLECTOR_MONASCA_OPTS)
ks_loading.register_session_conf_options(CONF, COLLECTOR_MONASCA_OPTS)

MONASCA_EXTRA_SCHEMA = {
    Required('extra_args', default={}): {
        # Key corresponding to the resource id in a metric's dimensions
        # Allows to adapt the resource identifier. Should not need to be
        # modified in a standard OpenStack installation
        Required('resource_key', default='resource_id'):
            All(str, Length(min=1)),
        Required('aggregation_method', default='max'):
            In(['max', 'mean', 'min']),
        # In case the metrics in Monasca do not belong to the project
        # cloudkitty is identified in
        Required('forced_project_id', default=''): str,
    },
}


class MonascaCollector(collector.BaseCollector):
    collector_name = 'monasca'

    @staticmethod
    def check_configuration(conf):
        conf = collector.BaseCollector.check_configuration(conf)
        metric_schema = Schema(collector.METRIC_BASE_SCHEMA).extend(
            MONASCA_EXTRA_SCHEMA)

        output = {}
        for metric_name, metric in conf.items():
            met = output[metric_name] = metric_schema(metric)

            if met['extra_args']['resource_key'] not in met['groupby']:
                met['groupby'].append(met['extra_args']['resource_key'])

        return output

    def __init__(self, **kwargs):
        super(MonascaCollector, self).__init__(**kwargs)
        self._conn = mon_client_utils.get_monasca_client(
            CONF, COLLECTOR_MONASCA_OPTS)

    def _get_metadata(self, metric_name, conf):
        info = {}
        info['unit'] = conf['metrics'][metric_name]['unit']

        dimension_names = self._conn.metric.list_dimension_names(
            metric_name=metric_name)
        info['metadata'] = [d['dimension_name'] for d in dimension_names]
        return info

    # NOTE(lukapeschke) if anyone sees a better way to do this,
    # please make a patch
    @classmethod
    def get_metadata(cls, resource_type, conf):
        tmp = cls(period=conf['period'])
        return tmp._get_metadata(resource_type, conf)

    def _get_dimensions(self, metric_name, project_id, q_filter):
        dimensions = {}
        scope_key = CONF.collect.scope_key
        if project_id:
            dimensions[scope_key] = project_id
        if q_filter:
            dimensions.update(q_filter)
        return dimensions

    def _fetch_measures(self, metric_name, start, end,
                        project_id=None, q_filter=None):
        """Get measures for given metric during the timeframe.

        :param metric_name: metric name to filter on.
        :type metric_name: str
        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param project_id: Filter on a specific tenant/project.
        :type project_id: str
        :param q_filter: Append a custom filter.
        :type q_filter: list
        """

        dimensions = self._get_dimensions(metric_name, project_id, q_filter)
        group_by = self.conf[metric_name]['groupby']

        # NOTE(lpeschke): One aggregated measure per collect period
        period = int((end - start).total_seconds())

        extra_args = self.conf[metric_name]['extra_args']
        kwargs = {}
        if extra_args['forced_project_id']:
            if extra_args['forced_project_id'] == 'SCOPE_ID' and project_id:
                kwargs['tenant_id'] = project_id
                dimensions.pop(CONF.collect.scope_key, None)
            else:
                kwargs['tenant_id'] = extra_args['forced_project_id']

        return self._conn.metrics.list_statistics(
            name=metric_name,
            merge_metrics=True,
            dimensions=dimensions,
            start_time=start,
            end_time=end,
            period=period,
            statistics=extra_args['aggregation_method'],
            group_by=group_by,
            **kwargs)

    def _fetch_metrics(self, metric_name, start, end,
                       project_id=None, q_filter=None):
        """List active metrics during the timeframe.

        :param metric_name: metric name to filter on.
        :type metric_name: str
        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param project_id: Filter on a specific tenant/project.
        :type project_id: str
        :param q_filter: Append a custom filter.
        :type q_filter: list
        """
        dimensions = self._get_dimensions(metric_name, project_id, q_filter)
        metrics = self._conn.metrics.list(
            name=metric_name,
            dimensions=dimensions,
            start_time=start,
            end_time=end,
        )

        resource_key = self.conf[metric_name]['extra_args']['resource_key']

        return {metric['dimensions'][resource_key]:
                metric['dimensions'] for metric in metrics}

    def _format_data(self, metconf, data, resources_info=None):
        """Formats Monasca data to CK data.

        Returns metadata, groupby and qty

        """
        groupby = data['dimensions']

        resource_key = metconf['extra_args']['resource_key']
        metadata = dict()
        if resources_info:
            resource = resources_info[groupby[resource_key]]
            for i in metconf['metadata']:
                metadata[i] = resource.get(i, '')

        qty = data['statistics'][0][1]
        converted_qty = ck_utils.convert_unit(
            qty, metconf['factor'], metconf['offset'])
        mutated_qty = ck_utils.mutate(converted_qty, metconf['mutate'])
        return metadata, groupby, mutated_qty

    def fetch_all(self, metric_name, start, end,
                  project_id=None, q_filter=None):
        met = self.conf[metric_name]

        data = self._fetch_measures(
            metric_name,
            start,
            end,
            project_id=project_id,
            q_filter=q_filter,
        )

        resources_info = None
        if met['metadata']:
            resources_info = self._fetch_metrics(
                metric_name,
                start,
                end,
                project_id=project_id,
                q_filter=q_filter,
            )

        formated_resources = list()
        for d in data:
            if len(d['statistics']):
                metadata, groupby, qty = self._format_data(
                    met, d, resources_info)
                formated_resources.append(dataframe.DataPoint(
                    met['unit'],
                    qty,
                    0,
                    groupby,
                    metadata,
                ))
        return formated_resources
