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
import abc
import datetime
import fractions

from oslo_config import cfg
from oslo_log import log as logging
from stevedore import driver
from voluptuous import All
from voluptuous import Any
from voluptuous import Coerce
from voluptuous import Error as VoluptuousError
from voluptuous import In
from voluptuous import Invalid
from voluptuous import Length
from voluptuous import Optional
from voluptuous import Required
from voluptuous import Schema

from cloudkitty.dataframe import DataPoint
from cloudkitty import utils as ck_utils

LOG = logging.getLogger(__name__)

collect_opts = [
    cfg.StrOpt('collector',
               default='gnocchi',
               help='Data collector.'),
    cfg.IntOpt('period',
               default=3600,
               help='Rating period in seconds.'),
    cfg.IntOpt('wait_periods',
               default=2,
               help='Wait for N periods before collecting new data.'),
    cfg.StrOpt('metrics_conf',
               default='/etc/cloudkitty/metrics.yml',
               help='Metrology configuration file.'),
    cfg.StrOpt('scope_key',
               default='project_id',
               help='Key defining a scope. project_id or domain_id for '
               'OpenStack, but can be anything.'),
]

CONF = cfg.CONF
CONF.register_opts(collect_opts, 'collect')

COLLECTORS_NAMESPACE = 'cloudkitty.collector.backends'


def MetricDict(value):
    if isinstance(value, dict) and len(value.keys()) > 0:
        return value
    raise Invalid("Not a dict with at least one key")


CONF_BASE_SCHEMA = {Required('metrics'): MetricDict}

METRIC_BASE_SCHEMA = {
    # Human-readable description for the CloudKitty rating type
    Optional('description'): All(str, Length(min=1)),
    # Display unit
    Required('unit'): All(str, Length(min=1)),
    # Factor for unit converion
    Required('factor', default=1):
        Any(int, float, Coerce(fractions.Fraction)),
    # Offset for unit conversion
    Required('offset', default=0):
        # [int, float, fractions.Fraction],
        Any(int, float, Coerce(fractions.Fraction)),
    # Name to be used in dataframes, and used for service creation in hashmap
    # module. Defaults to the name of the metric
    Optional('alt_name'): All(str, Length(min=1)),
    # This is what metrics are grouped by on collection.
    Required('groupby', default=list): [
        All(str, Length(min=1))
    ],
    # Available in HashMap
    Required('metadata', default=list): [
        All(str, Length(min=1))
    ],
    # Mutate collected value. May be any of:
    # (NONE, NUMBOOL, NOTNUMBOOL, FLOOR, CEIL).
    # Defaults to NONE
    Required('mutate', default='NONE'):
        In(['NONE', 'NUMBOOL', 'NOTNUMBOOL', 'FLOOR', 'CEIL', 'MAP']),
    # Map dict used if mutate == 'MAP'
    Optional('mutate_map'): dict,
    # Collector-specific args. Should be overriden by schema provided for
    # the given collector
    Optional('extra_args'): dict,
}


def get_collector():
    metrics_conf = ck_utils.load_conf(CONF.collect.metrics_conf)
    collector_args = {
        'period': CONF.collect.period,
        'conf': metrics_conf,
    }
    return driver.DriverManager(
        COLLECTORS_NAMESPACE,
        CONF.collect.collector,
        invoke_on_load=True,
        invoke_kwds=collector_args).driver


def get_collector_without_invoke():
    """Return the collector without invoke it."""
    return driver.DriverManager(
        COLLECTORS_NAMESPACE,
        CONF.collect.collector,
        invoke_on_load=False
    ).driver


def get_metrics_based_collector_metadata():
    """Return dict of metadata.

    Results are based on enabled collector and metrics in CONF.
    """
    metrics_conf = ck_utils.load_conf(CONF.collect.metrics_conf)
    collector = get_collector_without_invoke()
    metadata = {}
    if 'metrics' in metrics_conf:
        for metric_name, metric in metrics_conf.get('metrics', {}).items():
            alt_name = metric.get('alt_name', metric_name)
            metadata[alt_name] = collector.get_metadata(
                metric_name,
                metrics_conf,
            )
    return metadata


class NoDataCollected(Exception):
    """Raised when the collection returned no data.

    """

    def __init__(self, collector, resource):
        super(NoDataCollected, self).__init__(
            "Collector '%s' returned no data for resource '%s'" % (
                collector, resource))
        self.collector = collector
        self.resource = resource


class BaseCollector(object, metaclass=abc.ABCMeta):
    collector_name = None

    def __init__(self, **kwargs):
        try:
            self.period = kwargs['period']
            self.conf = self.check_configuration(kwargs['conf'])
        except KeyError as e:
            key_error_message = "Missing argument (%s)" % e
            LOG.error(key_error_message, e)
            raise ValueError(key_error_message)
        except VoluptuousError as v:
            LOG.error('Problem while checking configurations.', v)
            raise v

    @staticmethod
    def check_configuration(conf):
        """Checks and validates metric configuration.

        Collectors requiring extra parameters for metric collection
        should implement this method, call the method of the parent class,
        extend the ``extra_args`` key in ``METRIC_BASE_SCHEMA`` and validate
        the metric configuration against the new schema.
        """
        conf = Schema(CONF_BASE_SCHEMA)(conf)
        metric_schema = Schema(METRIC_BASE_SCHEMA)

        scope_key = CONF.collect.scope_key

        output = {}
        for metric_name, metric in conf['metrics'].items():
            output[metric_name] = metric_schema(metric)
            if scope_key not in output[metric_name]['groupby']:
                output[metric_name]['groupby'].append(scope_key)

        return output

    @classmethod
    def _res_to_func(cls, resource_name):
        trans_resource = 'get_'
        trans_resource += resource_name.replace('.', '_')
        return trans_resource

    @classmethod
    def get_metadata(cls, resource_name):
        """Return metadata about collected resource as a dict.

           Dict object should contain:
                - "metadata": available metadata list,
                - "unit": collected quantity unit
        """
        return {"metadata": [], "unit": "undefined"}

    @abc.abstractmethod
    def fetch_all(self, metric_name, start, end,
                  project_id=None, q_filter=None):
        """Fetches information about a specific metric for a given period.

        This method must respect the ``groupby`` and ``metadata`` arguments
        provided in the metric conf at initialization.
        (Available in ``self.conf['groupby']`` and ``self.conf['metadata']``).

        Returns a list of cloudkitty.dataframe.DataPoint objects.

        :param metric_name: Name of the metric to fetch
        :type metric_name: str
        :param start: start of the period
        :type start: datetime.datetime
        :param end: end of the period
        :type end: datetime.datetime
        :param project_id: ID of the scope for which data should be collected
        :type project_id: str
        :param q_filter: Optional filters
        :type q_filter: dict
        """

    def retrieve(self, metric_name, start, end,
                 project_id=None, q_filter=None):

        data = self.fetch_all(
            metric_name,
            start,
            end,
            project_id,
            q_filter=q_filter,
        )

        name = self.conf[metric_name].get('alt_name', metric_name)
        if not data:
            raise NoDataCollected(self.collector_name, name)

        return name, data

    def _create_data_point(self, metric, qty, price, groupby, metadata, start):
        unit = metric['unit']
        if not start:
            start = datetime.datetime.now()
            LOG.debug("Collector [%s]. No start datetime defined for "
                      "datapoint[unit=%s, quantity=%s, price=%s, groupby=%s, "
                      "metadata=%s]. Therefore, we use the current time as "
                      "the start time for this datapoint.",
                      self.collector_name, unit, qty, price, groupby, metadata)

        week_of_the_year = start.strftime("%U")
        day_of_the_year = start.strftime("%-j")
        month_of_the_year = start.strftime("%-m")
        year = start.strftime("%Y")

        if groupby is None:
            groupby = {}

        groupby['week_of_the_year'] = week_of_the_year
        groupby['day_of_the_year'] = day_of_the_year
        groupby['month'] = month_of_the_year
        groupby['year'] = year

        return DataPoint(unit, qty, price, groupby, metadata,
                         metric.get('description'))


class InvalidConfiguration(Exception):
    pass


def check_duplicates(metric_name, metric):
    """Checks for duplicates in "groupby" and "metadata".

    :param metric: config dict for a metric to check
    :type metric: dict
    """
    groupby = set(metric['groupby'])
    metadata = set(metric['metadata'])
    duplicates = groupby.intersection(metadata)
    if duplicates:
        raise InvalidConfiguration(
            'Metric {} has duplicates in groupby and metadata: {}'.format(
                metric_name, metric))

    metric['groupby'] = list(groupby)
    metric['metadata'] = list(metadata)
    return metric


def validate_map_mutator(metric_name, metric):
    """Validates MAP mutator"""
    mutate = metric.get('mutate')
    mutate_map = metric.get('mutate_map')

    if mutate == 'MAP' and mutate_map is None:
        raise InvalidConfiguration(
            'Metric {} uses MAP mutator but mutate_map is missing: {}'.format(
                metric_name, metric))

    if mutate != 'MAP' and mutate_map is not None:
        raise InvalidConfiguration(
            'Metric {} not using MAP mutator but mutate_map is present: '
            '{}'.format(metric_name, metric))


def validate_conf(conf):
    """Validates the provided configuration."""
    collector = get_collector_without_invoke()
    output = collector.check_configuration(conf)
    for metric_name, metric in output.items():
        if 'alt_name' not in metric.keys():
            metric['alt_name'] = metric_name
        check_duplicates(metric_name, metric)
        validate_map_mutator(metric_name, metric)
    return output
