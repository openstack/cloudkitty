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
import copy
from datetime import timedelta
import requests

from gnocchiclient import auth as gauth
from gnocchiclient import client as gclient
from gnocchiclient import exceptions as gexceptions
from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging
from voluptuous import All
from voluptuous import In
from voluptuous import Invalid
from voluptuous import Length
from voluptuous import Range
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import collector
from cloudkitty.common import custom_session
from cloudkitty import utils as ck_utils
from cloudkitty.utils import tz as tzutils

LOG = logging.getLogger(__name__)

COLLECTOR_GNOCCHI_OPTS = 'collector_gnocchi'


def GnocchiMetricDict(value):
    if isinstance(value, dict) and len(value.keys()) > 0:
        return value
    if isinstance(value, list) and len(value) > 0:
        for v in value:
            if not (isinstance(v, dict) and len(v.keys()) > 0):
                raise Invalid("Not a dict with at least one key or a "
                              "list with at least one dict with at "
                              "least one key. Provided value: %s" % value)
        return value
    raise Invalid("Not a dict with at least one key or a "
                  "list with at least one dict with at "
                  "least one key. Provided value: %s" % value)


GNOCCHI_CONF_SCHEMA = {Required('metrics'): GnocchiMetricDict}

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
    (str(i) + 'pct' for i in range(1, 100)))

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
        Required('use_all_resource_revisions', default=True): All(bool),
        # Provide means for operators to customize the aggregation query
        # executed against Gnocchi. By default we use the following:
        #
        # '(aggregate RE_AGGREGATION_METHOD
        #   (metric METRIC_NAME AGGREGATION_METHOD))'
        #
        # Therefore, this option enables operators to take full advantage of
        # operations available in Gnocchi, such as any arithmetic operations,
        # logical operations and many others.
        #
        # When using a custom aggregation query, you can keep the placeholders
        # 'RE_AGGREGATION_METHOD', 'AGGREGATION_METHOD', and 'METRIC_NAME':
        # they will be replaced at runtime by values from the metric
        # configuration.
        Required('custom_query', default=''): All(str),
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
        conf = Schema(GNOCCHI_CONF_SCHEMA)(conf)
        conf = copy.deepcopy(conf)
        scope_key = CONF.collect.scope_key
        metric_schema = Schema(collector.METRIC_BASE_SCHEMA).extend(
            GNOCCHI_EXTRA_SCHEMA)

        output = {}
        for metric_name, metric in conf['metrics'].items():
            if not isinstance(metric, list):
                metric = [metric]
            for m in metric:
                met = metric_schema(m)
                m.update(met)
                if scope_key not in m['groupby']:
                    m['groupby'].append(scope_key)
                if met['extra_args']['resource_key'] not in m['groupby']:
                    m['groupby'].append(met['extra_args']['resource_key'])

                names = [metric_name]
                alt_name = met.get('alt_name')
                if alt_name is not None:
                    names.append(alt_name)
                new_metric_name = "@#".join(names)
                output[new_metric_name] = m

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
                if 'Metrics not found' not in e.message["cause"]:
                    raise
            LOG.warning('[{scope}] Skipping this metric for the '
                        'current cycle.'.format(scope=project_id))
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
            'use_history': True,
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

        op = self.generate_aggregation_operation(extra_args, metric_name)

        LOG.debug("Aggregation operation [%s] used to retrieve metric [%s].",
                  op, metric_name)
        return op

    @staticmethod
    def generate_aggregation_operation(extra_args, metric_name):
        metric_name = metric_name.split('@#')[0]
        aggregation_method = extra_args['aggregation_method']
        re_aggregation_method = aggregation_method

        if 're_aggregation_method' in extra_args:
            re_aggregation_method = extra_args['re_aggregation_method']

        op = ["aggregate", re_aggregation_method,
              ["metric", metric_name, aggregation_method]]

        custom_gnocchi_query = extra_args.get('custom_query')
        if custom_gnocchi_query:
            LOG.debug("Using custom Gnocchi query [%s] with metric [%s].",
                      custom_gnocchi_query, metric_name)
            op = custom_gnocchi_query.replace(
                'RE_AGGREGATION_METHOD', re_aggregation_method).replace(
                'AGGREGATION_METHOD', aggregation_method).replace(
                'METRIC_NAME', metric_name)

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
        mutate_map = metconf.get('mutate_map')
        mutated_qty = ck_utils.mutate(converted_qty, metconf['mutate'],
                                      mutate_map=mutate_map)
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

        data = GnocchiCollector.filter_unecessary_measurements(
            data, met, metric_name)

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
            LOG.debug("Processing entry [%s] for [%s] in timestamp ["
                      "start=%s, end=%s] and project id [%s]", d,
                      metric_name, start, end, project_id)
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
                point = self._create_data_point(met, qty, 0, groupby,
                                                metadata, start)
                formated_resources.append(point)

        return formated_resources

    @staticmethod
    def filter_unecessary_measurements(data, met, metric_name):
        """Filter unecessary measurements if not 'use_all_resource_revisions'

        The option 'use_all_resource_revisions' is useful when using Gnocchi
        with the patch introduced in
        https://github.com/gnocchixyz/gnocchi/pull/1059.

        That patch can cause queries to return more than one entry per
        granularity (timespan), according to the revisions a resource has.
        This can be problematic when using the 'mutate' option of Cloudkitty.
        Therefore, this option ('use_all_resource_revisions') allows operators
        to discard all datapoints returned from Gnocchi, but the last one in
        the granularity queried by CloudKitty. The default behavior is
        maintained, which means, CloudKitty always use all the data points
        returned.

        When the 'mutate' option is not used, we need to sum all the
        quantities, and use this value with the latest version of the
        attributes received. Otherwise, we will miss the complete accounting
        for the time frame where the revision happened.
        """

        use_all_resource_revisions = met[
            'extra_args']['use_all_resource_revisions']

        LOG.debug("Configuration use_all_resource_revisions set to [%s] for "
                  "metric [%s]", use_all_resource_revisions, metric_name)

        if data and not use_all_resource_revisions:
            if "id" not in data[0].get('group', {}).keys():
                LOG.debug("There is no ID id in the groupby section and we "
                          "are trying to use 'use_all_resource_revisions'. "
                          "However, without an ID there is not much we can do "
                          "to identify the revisions for a resource.")
                return data

            original_data = copy.deepcopy(data)
            # Here we order the data in a way to maintain the latest revision
            # as the principal element to be used. We are assuming that there
            # is a revision_start attribute, which denotes when the revision
            # was created. If there is no revision start, we cannot do much.
            data.sort(key=lambda x: (x["group"]["id"],
                                     x["group"]["revision_start"]),
                      reverse=False)

            # We just care about the oldest entry per resource in the
            # given time slice (configured granularity in Cloudkitty) regarding
            # the attributes. For the quantity, we still want to use all the
            # quantity elements summing up the value for all the revisions.
            map_id_entry = {d["group"]['id']: d for d in data}
            single_entries_per_id = list(map_id_entry.values())

            GnocchiCollector.zero_quantity_values(single_entries_per_id)

            for element in original_data:
                LOG.debug("Processing entry [%s] for original data from "
                          "Gnocchi to sum all of the revisions if needed for "
                          "metric [%s].", element, metric_name)
                group_entry = element.get('group')
                if not group_entry:
                    LOG.warning("No groupby section found for element [%s].",
                                element)
                    continue

                entry_id = group_entry.get('id')
                if not entry_id:
                    LOG.warning("No ID attribute found for element [%s].",
                                element)
                    continue

                first_measure = element.get('measures')
                if first_measure:
                    second_measure = first_measure.get('measures')
                    if second_measure:
                        aggregated_value = second_measure.get('aggregated', [])
                        if len(aggregated_value) == 1:
                            actual_aggregated_value = aggregated_value[0]

                            if len(actual_aggregated_value) == 3:
                                value_to_add = actual_aggregated_value[2]
                                entry = map_id_entry[entry_id]
                                old_value = list(
                                    entry['measures']['measures'][
                                        'aggregated'][0])

                                new_value = copy.deepcopy(old_value)
                                new_value[2] += value_to_add
                                entry['measures']['measures'][
                                    'aggregated'][0] = tuple(new_value)

                                LOG.debug("Adding value [%s] to value [%s] "
                                          "in entry [%s] for metric [%s].",
                                          value_to_add, old_value, entry,
                                          metric_name)

            LOG.debug("Replaced list of data points [%s] with [%s] for "
                      "metric [%s]", original_data, single_entries_per_id,
                      metric_name)

            data = single_entries_per_id
        return data

    @staticmethod
    def zero_quantity_values(single_entries_per_id):
        """Cleans the quantity value of the entry for further processing."""
        for single_entry in single_entries_per_id:
            first_measure = single_entry.get('measures')
            if first_measure:
                second_measure = first_measure.get('measures')
                if second_measure:
                    aggregated_value = second_measure.get('aggregated', [])

                    if len(aggregated_value) == 1:
                        actual_aggregated_value = aggregated_value[0]

                        # We need to convert the tuple to a list
                        actual_aggregated_value = list(actual_aggregated_value)
                        if len(actual_aggregated_value) == 3:
                            LOG.debug("Zeroing aggregated value for single "
                                      "entry [%s].", single_entry)
                            # We are going to zero this elements, as we
                            # will be summing all of them later.
                            actual_aggregated_value[2] = 0

                            # Convert back to tuple
                            aggregated_value[0] = tuple(
                                actual_aggregated_value)
                        else:
                            LOG.warning("We expect the actual aggregated "
                                        "value to be a list of 3 elements."
                                        " The first one is a timestamp, "
                                        "the second the granularity, and "
                                        "the last one the quantity "
                                        "measured. But we got a different "
                                        "structure: [%s]. for entry [%s].",
                                        actual_aggregated_value,
                                        single_entry)
                    else:
                        LOG.warning("Aggregated value return does not "
                                    "have the expected size. Expected 1, "
                                    "but got [%s].", len(aggregated_value))
                else:
                    LOG.debug('Second measure of the aggregates API for '
                              'entry [%s] is empty.', single_entry)
            else:
                LOG.debug('First measure of the aggregates API for entry '
                          '[%s] is empty.', single_entry)
