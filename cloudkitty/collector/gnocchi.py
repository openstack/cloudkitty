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
from datetime import timedelta
import requests
import six

from gnocchiclient import auth as gauth
from gnocchiclient import client as gclient
from gnocchiclient import exceptions as gexceptions
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging
from voluptuous import All
from voluptuous import In
from voluptuous import Length
from voluptuous import Range
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import collector
from cloudkitty.common import custom_session
from cloudkitty import dataframe
from cloudkitty import utils as ck_utils
from cloudkitty.utils import tz as tzutils


LOG = logging.getLogger(__name__)

COLLECTOR_GNOCCHI_OPTS = 'collector_gnocchi'

collector_gnocchi_opts = [
    cfg.StrOpt(
        'gnocchi_auth_type',
        default='keystone',
        choices=['keystone', 'basic'],
        help='Gnocchi auth type (keystone or basic). Keystone credentials '
        'can be specified through the "auth_section" parameter',
    ),
    cfg.StrOpt(
        'gnocchi_user',
        default='',
        help='Gnocchi user (for basic auth only)',
    ),
    cfg.StrOpt(
        'gnocchi_endpoint',
        default='',
        help='Gnocchi endpoint (for basic auth only)',
    ),
    cfg.StrOpt(
        'interface',
        default='internalURL',
        help='Endpoint URL type (for keystone auth only)',
    ),
    cfg.StrOpt(
        'region_name',
        default='RegionOne',
        help='Region Name',
    ),
    cfg.IntOpt(
        'http_pool_maxsize',
        default=requests.adapters.DEFAULT_POOLSIZE,
        help='If the value is not defined, we use the value defined by '
             'requests.adapters.DEFAULT_POOLSIZE',
    )
]

ks_loading.register_session_conf_options(cfg.CONF, COLLECTOR_GNOCCHI_OPTS)
ks_loading.register_auth_conf_options(cfg.CONF, COLLECTOR_GNOCCHI_OPTS)
cfg.CONF.register_opts(collector_gnocchi_opts, COLLECTOR_GNOCCHI_OPTS)

CONF = cfg.CONF

# According to 'gnocchi/rest/aggregates/operations.py#AGG_MAP' and
# 'gnocchi/rest/aggregates/operations.py#AGG_MAP' the following are the basic
# aggregation methods that one can use when configuring an aggregation
# method in the archive policy in Gnocchi or using the aggregation API.
BASIC_AGGREGATION_METHODS = set(('mean', 'sum', 'last', 'max', 'min', 'std',
                                 'median', 'first', 'count'))
for agg in list(BASIC_AGGREGATION_METHODS):
    BASIC_AGGREGATION_METHODS.add("rate:%s" % agg)

EXTRA_AGGREGATION_METHODS_FOR_ARCHIVE_POLICY = set(
    (str(i) + 'pct' for i in six.moves.range(1, 100)))

for agg in list(EXTRA_AGGREGATION_METHODS_FOR_ARCHIVE_POLICY):
    EXTRA_AGGREGATION_METHODS_FOR_ARCHIVE_POLICY.add("rate:%s" % agg)

# The aggregation method that one can use to configure the archive
# policies also supports the 'pct' (percentile) operation. Therefore,
# we also expose this as a configuration.
VALID_AGGREGATION_METHODS_FOR_METRICS = BASIC_AGGREGATION_METHODS.union(
    EXTRA_AGGREGATION_METHODS_FOR_ARCHIVE_POLICY)

GNOCCHI_EXTRA_SCHEMA = {
    Required('extra_args'): {
        Required('resource_type'): All(str, Length(min=1)),
        # Due to Gnocchi model, metric are grouped by resource.
        # This parameter permits to adapt the key of the resource identifier
        Required('resource_key', default='id'): All(str, Length(min=1)),
        Required('aggregation_method', default='max'):
            In(VALID_AGGREGATION_METHODS_FOR_METRICS),
        Required('re_aggregation_method', default='max'):
            In(BASIC_AGGREGATION_METHODS),
        Required('force_granularity', default=3600): All(int, Range(min=0)),
    },
}


class AssociatedResourceNotFound(Exception):
    """Exception raised when no resource can be associated with a metric."""

    def __init__(self, resource_key, resource_id):
        super(AssociatedResourceNotFound, self).__init__(
            'Resource with {}={} could not be found'.format(
                resource_key, resource_id),
        )


class GnocchiCollector(collector.BaseCollector):

    collector_name = 'gnocchi'

    def __init__(self, **kwargs):
        super(GnocchiCollector, self).__init__(**kwargs)

        adapter_options = {'connect_retries': 3}
        if CONF.collector_gnocchi.gnocchi_auth_type == 'keystone':
            auth_plugin = ks_loading.load_auth_from_conf_options(
                CONF,
                COLLECTOR_GNOCCHI_OPTS,
            )
            adapter_options['interface'] = CONF.collector_gnocchi.interface
        else:
            auth_plugin = gauth.GnocchiBasicPlugin(
                user=CONF.collector_gnocchi.gnocchi_user,
                endpoint=CONF.collector_gnocchi.gnocchi_endpoint,
            )
        adapter_options['region_name'] = CONF.collector_gnocchi.region_name

        verify = True
        if CONF.collector_gnocchi.cafile:
            verify = CONF.collector_gnocchi.cafile
        elif CONF.collector_gnocchi.insecure:
            verify = False

        self._conn = gclient.Client(
            '1',
            session=custom_session.create_custom_session(
                {'auth': auth_plugin, 'verify': verify},
                CONF.collector_gnocchi.http_pool_maxsize),
            adapter_options=adapter_options,
        )

    @staticmethod
    def check_configuration(conf):
        """Check metrics configuration

        """
        conf = collector.BaseCollector.check_configuration(conf)
        metric_schema = Schema(collector.METRIC_BASE_SCHEMA).extend(
            GNOCCHI_EXTRA_SCHEMA)

        output = {}
        for metric_name, metric in conf.items():
            met = output[metric_name] = metric_schema(metric)

            if met['extra_args']['resource_key'] not in met['groupby']:
                met['groupby'].append(met['extra_args']['resource_key'])

        return output

    @classmethod
    def get_metadata(cls, resource_name, conf):
        info = super(GnocchiCollector, cls).get_metadata(resource_name)
        try:
            info["metadata"].extend(
                conf[resource_name]['groupby']
            ).extend(
                conf[resource_name]['metadata']
            )
            info['unit'] = conf[resource_name]['unit']
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
            self.gen_filter(cop=">=", ended_at=start.isoformat()),
            lop='or'))
        time_filter.append(
            self.gen_filter(cop="<=", started_at=end.isoformat()))
        return time_filter

    def _fetch_resources(self, metric_name, start, end,
                         project_id=None, q_filter=None):
        """Get resources during the timeframe.

        :type metric_name: str
        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param project_id: Filter on a specific tenant/project.
        :type project_id: str
        :param q_filter: Append a custom filter.
        :type q_filter: list
        """

        # Get gnocchi specific conf
        extra_args = self.conf[metric_name]['extra_args']
        resource_type = extra_args['resource_type']
        scope_key = CONF.collect.scope_key

        # Build query

        # FIXME(peschk_l): In order not to miss any resource whose metrics may
        # contain measures after its destruction, we scan resources over three
        # collect periods.
        delta = timedelta(seconds=CONF.collect.period)
        start = tzutils.substract_delta(start, delta)
        end = tzutils.add_delta(end, delta)
        query_parameters = self._generate_time_filter(start, end)

        if project_id:
            kwargs = {scope_key: project_id}
            query_parameters.append(self.gen_filter(**kwargs))
        if q_filter:
            query_parameters.append(q_filter)

        sorts = [extra_args['resource_key'] + ':asc']
        resources = []
        marker = None
        while True:
            resources_chunk = self._conn.resource.search(
                resource_type=resource_type,
                query=self.extend_filter(*query_parameters),
                sorts=sorts,
                marker=marker)
            if len(resources_chunk) < 1:
                break
            resources += resources_chunk
            marker = resources_chunk[-1][extra_args['resource_key']]
        return {res[extra_args['resource_key']]: res for res in resources}

    def _fetch_metric(self, metric_name, start, end,
                      project_id=None, q_filter=None):
        """Get metric during the timeframe.

        :param metric_name: metric name to filter on.
        :param start: Start of the timeframe.
        :param end: End of the timeframe if needed.
        :param project_id: Filter on a specific tenant/project.
        :type project_id: str
        :param q_filter: Append a custom filter.
        :type q_filter: list
        """
        agg_kwargs = self.get_aggregation_api_arguments(end, metric_name,
                                                        project_id,
                                                        q_filter,
                                                        start)

        op = self.build_operation_command(metric_name)
        try:
            measurements = self._conn.aggregates.fetch(op, **agg_kwargs)
            LOG.debug("Measurements [%s] received with operation [%s] and "
                      "arguments [%s].", measurements, op, agg_kwargs)
            return measurements
        except (gexceptions.MetricNotFound, gexceptions.BadRequest) as e:
            # FIXME(peschk_l): gnocchiclient seems to be raising a BadRequest
            # when it should be raising MetricNotFound
            if isinstance(e, gexceptions.BadRequest):
                if 'Metrics not found' not in six.text_type(e):
                    raise
            LOG.warning('[{scope}] Skipping this metric for the '
                        'current cycle.'.format(scope=project_id, err=e))
            return []

    def get_aggregation_api_arguments(self, end, metric_name, project_id,
                                      q_filter, start):
        extra_args = self.conf[metric_name]['extra_args']
        resource_type = extra_args['resource_type']

        query_parameters = self.build_query_parameters(project_id, q_filter,
                                                       resource_type)
        agg_kwargs = {
            'resource_type': resource_type,
            'start': start,
            'stop': end,
            'groupby': self.conf[metric_name]['groupby'],
            'search': self.extend_filter(*query_parameters),
        }

        force_granularity = extra_args['force_granularity']
        if force_granularity > 0:
            agg_kwargs['granularity'] = force_granularity

        re_aggregation_method = extra_args['re_aggregation_method']
        if re_aggregation_method.startswith('rate:'):
            agg_kwargs['start'] = start - timedelta(seconds=force_granularity)
            LOG.debug("Re-aggregation method for metric [%s] configured as"
                      " [%s]. Therefore, we need two data points. Start date"
                      " modified from [%s] to [%s].", metric_name,
                      re_aggregation_method, start, agg_kwargs['start'])

        return agg_kwargs

    def build_query_parameters(self, project_id, q_filter, resource_type):
        query_parameters = list()
        query_parameters.append(
            self.gen_filter(cop="=", type=resource_type))
        if project_id:
            scope_key = CONF.collect.scope_key
            kwargs = {scope_key: project_id}
            query_parameters.append(self.gen_filter(**kwargs))
        if q_filter:
            query_parameters.append(q_filter)
        return query_parameters

    def build_operation_command(self, metric_name):
        extra_args = self.conf[metric_name]['extra_args']

        re_aggregation_method = extra_args['re_aggregation_method']
        op = ["aggregate", re_aggregation_method,
              ["metric", metric_name, extra_args['aggregation_method']]]
        return op

    def _format_data(self, metconf, data, resources_info=None):
        """Formats gnocchi data to CK data.

        Returns metadata, groupby and qty

        """
        groupby = data['group']
        # if resource info is provided, add additional
        # metadata as defined in the conf
        metadata = dict()
        if resources_info is not None:
            resource_key = metconf['extra_args']['resource_key']
            resource_id = groupby[resource_key]
            try:
                resource = resources_info[resource_id]
            except KeyError:
                raise AssociatedResourceNotFound(resource_key, resource_id)
            for i in metconf['metadata']:
                metadata[i] = resource.get(i, '')
        qty = data['measures']['measures']['aggregated'][0][2]
        converted_qty = ck_utils.convert_unit(
            qty, metconf['factor'], metconf['offset'])
        mutated_qty = ck_utils.mutate(converted_qty, metconf['mutate'])
        return metadata, groupby, mutated_qty

    def fetch_all(self, metric_name, start, end,
                  project_id=None, q_filter=None):

        met = self.conf[metric_name]

        data = self._fetch_metric(
            metric_name,
            start,
            end,
            project_id=project_id,
            q_filter=q_filter,
        )

        resources_info = None
        if met['metadata']:
            resources_info = self._fetch_resources(
                metric_name,
                start,
                end,
                project_id=project_id,
                q_filter=q_filter
            )
        formated_resources = list()
        for d in data:
            # Only if aggregates have been found
            if d['measures']['measures']['aggregated']:
                try:
                    metadata, groupby, qty = self._format_data(
                        met, d, resources_info)
                except AssociatedResourceNotFound as e:
                    LOG.warning(
                        '[{}] An error occured during data collection '
                        'between {} and {}: {}'.format(
                            project_id, start, end, e),
                    )
                    continue
                formated_resources.append(dataframe.DataPoint(
                    met['unit'],
                    qty,
                    0,
                    groupby,
                    metadata,
                ))
        return formated_resources
