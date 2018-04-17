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
import abc
import fractions

from oslo_config import cfg
import six
from stevedore import driver
from voluptuous import All
from voluptuous import Any
from voluptuous import Coerce
from voluptuous import In
from voluptuous import Invalid
from voluptuous import Length
from voluptuous import Optional
from voluptuous import Required
from voluptuous import Schema

from cloudkitty import transformer
from cloudkitty import utils as ck_utils

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
    # Mutate collected value. May be any of (NONE, NUMBOOL, FLOOR, CEIL).
    # Defaults to NONE
    Required('mutate', default='NONE'):
        In(['NONE', 'NUMBOOL', 'FLOOR', 'CEIL']),
    # Collector-specific args. Should be overriden by schema provided for
    # the given collector
    Optional('extra_args'): dict,
}


def get_collector(transformers=None):
    metrics_conf = ck_utils.load_conf(CONF.collect.metrics_conf)
    if not transformers:
        transformers = transformer.get_transformers()
    collector_args = {
        'period': CONF.collect.period,
        'transformers': transformers,
    }
    collector_args.update({'conf': metrics_conf})
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
    transformers = transformer.get_transformers()
    collector = get_collector_without_invoke()
    metadata = {}
    if 'metrics' in metrics_conf:
        for metric_name, metric in metrics_conf.get('metrics', {}).items():
            alt_name = metric.get('alt_name', metric_name)
            metadata[alt_name] = collector.get_metadata(
                metric_name,
                transformers,
                metrics_conf,
            )
    return metadata


class TransformerDependencyError(Exception):
    """Raised when a collector can't find a mandatory transformer."""

    def __init__(self, collector, transformer):
        super(TransformerDependencyError, self).__init__(
            "Transformer '%s' not found, but required by %s" % (transformer,
                                                                collector))
        self.collector = collector
        self.transformer = transformer


class NoDataCollected(Exception):
    """Raised when the collection returned no data.

    """

    def __init__(self, collector, resource):
        super(NoDataCollected, self).__init__(
            "Collector '%s' returned no data for resource '%s'" % (
                collector, resource))
        self.collector = collector
        self.resource = resource


@six.add_metaclass(abc.ABCMeta)
class BaseCollector(object):
    collector_name = None
    dependencies = ['CloudKittyFormatTransformer']

    def __init__(self, transformers, **kwargs):
        try:
            self.transformers = transformers
            self.period = kwargs['period']
            self.conf = self.check_configuration(kwargs['conf'])
        except KeyError as e:
            raise ValueError("Missing argument (%s)" % e)

        self._check_transformers()
        self.t_cloudkitty = self.transformers['CloudKittyFormatTransformer']

    def _check_transformers(self):
        """Check for transformer prerequisites

        """
        for dependency in self.dependencies:
            if dependency not in self.transformers:
                raise TransformerDependencyError(self.collector_name,
                                                 dependency)

    @staticmethod
    def check_configuration(self, conf):
        """Check metrics configuration

        """
        return Schema(METRIC_BASE_SCHEMA)(conf)

    @staticmethod
    def last_month():
        month_start = ck_utils.get_month_start()
        month_end = ck_utils.get_month_end()
        start_ts = ck_utils.dt2ts(month_start)
        end_ts = ck_utils.dt2ts(month_end)
        return start_ts, end_ts

    @staticmethod
    def current_month():
        month_start = ck_utils.get_month_start()
        return ck_utils.dt2ts(month_start)

    @classmethod
    def _res_to_func(cls, resource_name):
        trans_resource = 'get_'
        trans_resource += resource_name.replace('.', '_')
        return trans_resource

    @classmethod
    def get_metadata(cls, resource_name, transformers):
        """Return metadata about collected resource as a dict.

           Dict object should contain:
                - "metadata": available metadata list,
                - "unit": collected quantity unit
        """
        return {"metadata": [], "unit": "undefined"}

    @abc.abstractmethod
    def fetch_all(self, metric_name, start, end,
                  project_id=None, q_filter=None):
        pass

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
        if data:
            data = self.t_cloudkitty.format_service(name, data)
        if not data:
            raise NoDataCollected(self.collector_name, name)
        return data


def validate_conf(conf):
    """Validates the provided configuration."""
    collector = get_collector_without_invoke()
    output = collector.check_configuration(conf)
    for metric_name, metric in output.items():
        if 'alt_name' not in metric.keys():
            metric['alt_name'] = metric_name
    return output
