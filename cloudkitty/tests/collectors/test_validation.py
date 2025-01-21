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
import copy

from voluptuous import error as verror

from cloudkitty import collector
from cloudkitty import tests
from datetime import datetime
from datetime import timedelta


class MetricConfigValidationTest(tests.TestCase):

    base_data = {
        'metrics': {
            'metric_one': {
                'groupby': ['one'],
                'metadata': ['two'],
                'unit': 'u',
            }
        }
    }

    base_output = {
        'metric_one': {
            'groupby': ['one'],
            'metadata': ['two'],
            'unit': 'u',
            'factor': 1,
            'offset': 0,
            'mutate': 'NONE',
        }
    }

    list_data = {
        'metrics': {
            'metric_one': [
                {
                    'groupby': ['one'],
                    'metadata': ['two'],
                    'alt_name': 'metric_u',
                    'unit': 'u',
                },
                {
                    'groupby': ['three'],
                    'metadata': ['four'],
                    'alt_name': 'metric_v',
                    'unit': 'v',
                }
            ]
        }
    }

    list_output = {
        'metric_one@#metric_u': {
            'groupby': ['one'],
            'metadata': ['two'],
            'unit': 'u',
            'alt_name': 'metric_u',
            'factor': 1,
            'offset': 0,
            'mutate': 'NONE',
        },
        'metric_one@#metric_v': {
            'groupby': ['three'],
            'metadata': ['four'],
            'unit': 'v',
            'alt_name': 'metric_v',
            'factor': 1,
            'offset': 0,
            'mutate': 'NONE',
        },
    }

    def test_base_minimal_config(self):
        data = copy.deepcopy(self.base_data)
        expected_output = copy.deepcopy(self.base_output)
        expected_output['metric_one']['groupby'].append('project_id')

        self.assertEqual(
            collector.BaseCollector.check_configuration(data),
            expected_output,
        )

    def test_gnocchi_minimal_config_no_extra_args(self):
        data = copy.deepcopy(self.base_data)

        self.assertRaises(
            verror.MultipleInvalid,
            collector.gnocchi.GnocchiCollector.check_configuration,
            data,
        )

    def test_gnocchi_minimal_config_minimal_extra_args(self):
        data = copy.deepcopy(self.base_data)
        data['metrics']['metric_one']['extra_args'] = {'resource_type': 'res'}
        expected_output = copy.deepcopy(self.base_output)
        expected_output['metric_one']['groupby'] += ['project_id', 'id']
        expected_output['metric_one']['extra_args'] = {
            'aggregation_method': 'max',
            're_aggregation_method': 'max',
            'force_granularity': 3600,
            'resource_type': 'res',
            'resource_key': 'id',
            'use_all_resource_revisions': True,
            'custom_query': ''}

        self.assertEqual(
            collector.gnocchi.GnocchiCollector.check_configuration(data),
            expected_output,
        )

    def test_gnocchi_minimal_config_negative_forced_aggregation(self):
        data = copy.deepcopy(self.base_data)
        data['metrics']['metric_one']['extra_args'] = {
            'resource_type': 'res',
            'force_aggregation': -42,
        }

        self.assertRaises(
            verror.MultipleInvalid,
            collector.gnocchi.GnocchiCollector.check_configuration,
            data,
        )

    def test_prometheus_minimal_config_empty_extra_args(self):
        data = copy.deepcopy(self.base_data)
        data['metrics']['metric_one']['extra_args'] = {}

        expected_output = copy.deepcopy(self.base_output)
        expected_output['metric_one']['groupby'].append('project_id')
        expected_output['metric_one']['extra_args'] = {
            'aggregation_method': 'max',
            'query_prefix': '',
            'query_suffix': '',
        }
        self.assertEqual(
            collector.prometheus.PrometheusCollector.check_configuration(data),
            expected_output,
        )

    def test_prometheus_minimal_config_no_extra_args(self):
        data = copy.deepcopy(self.base_data)
        expected_output = copy.deepcopy(self.base_output)
        expected_output['metric_one']['groupby'].append('project_id')
        expected_output['metric_one']['extra_args'] = {
            'aggregation_method': 'max',
            'query_prefix': '',
            'query_suffix': '',
        }
        self.assertEqual(
            collector.prometheus.PrometheusCollector.check_configuration(data),
            expected_output,
        )

    def test_prometheus_minimal_config_minimal_extra_args(self):
        data = copy.deepcopy(self.base_data)
        data['metrics']['metric_one']['extra_args'] = {
            'aggregation_method': 'max',
            'query_function': 'abs',
            'query_prefix': 'custom_prefix',
            'query_suffix': 'custom_suffix',
            'range_function': 'delta',
        }
        expected_output = copy.deepcopy(self.base_output)
        expected_output['metric_one']['groupby'].append('project_id')
        expected_output['metric_one']['extra_args'] = {
            'aggregation_method': 'max',
            'query_function': 'abs',
            'query_prefix': 'custom_prefix',
            'query_suffix': 'custom_suffix',
            'range_function': 'delta',
        }

        self.assertEqual(
            collector.prometheus.PrometheusCollector.check_configuration(data),
            expected_output,
        )

    def test_prometheus_query_builder(self):
        data = copy.deepcopy(self.base_data)
        data['metrics']['metric_one']['extra_args'] = {
            'aggregation_method': 'max',
            'query_function': 'abs',
            'query_prefix': 'custom_prefix',
            'query_suffix': 'custom_suffix',
            'range_function': 'delta',
        }

        prometheus = collector.prometheus.PrometheusCollector

        conf = prometheus.check_configuration(data)
        metric_name = list(conf.keys())[0]
        start = datetime.now()
        end = start + timedelta(seconds=60)
        scope_key = "random_key"
        scope_id = "random_value"
        groupby = conf[metric_name].get('groupby', [])
        metadata = conf[metric_name].get('metadata', [])

        query = prometheus.build_query(
            conf,
            metric_name,
            start,
            end,
            scope_key,
            scope_id,
            groupby,
            metadata
        )

        expected_output = (
            'custom_prefix max(abs(delta(metric_one{random_key="random_value"}'
            '[60s]))) by (one, project_id, two) custom_suffix'
        )

        self.assertEqual(
            query,
            expected_output,
        )

    def test_check_duplicates(self):
        data = copy.deepcopy(self.base_data)
        for metric_name, metric in data['metrics'].items():
            metric['metadata'].append('one')
            self.assertRaises(
                collector.InvalidConfiguration,
                collector.check_duplicates, metric_name, metric)

    def test_validate_map_mutator(self):
        data = copy.deepcopy(self.base_data)

        # Check that validation succeeds when MAP mutator is not used
        for metric_name, metric in data['metrics'].items():
            collector.validate_map_mutator(metric_name, metric)

        # Check that validation raises an exception when mutate_map is missing
        for metric_name, metric in data['metrics'].items():
            metric['mutate'] = 'MAP'
            self.assertRaises(
                collector.InvalidConfiguration,
                collector.validate_map_mutator, metric_name, metric)

        data = copy.deepcopy(self.base_data)
        # Check that validation raises an exception when mutate_map is present
        # but MAP mutator is not used
        for metric_name, metric in data['metrics'].items():
            metric['mutate_map'] = {}
            self.assertRaises(
                collector.InvalidConfiguration,
                collector.validate_map_mutator, metric_name, metric)

    def test_base_minimal_config_list(self):
        data = copy.deepcopy(self.list_data)
        expected_output = copy.deepcopy(self.list_output)

        for _, metric in expected_output.items():
            metric['groupby'].append('project_id')

        self.assertEqual(
            collector.BaseCollector.check_configuration(data),
            expected_output,
        )

    # submetric with same alt_name should fail
    # Because they would overlap in the dict
    def test_check_duplicates_list(self):
        data = copy.deepcopy(self.list_data)
        data['metrics']['metric_one'].append({
            'groupby': ['five'],
            'metadata': ['six'],
            'alt_name': 'metric_v',
            'unit': 'w',
        })
        self.assertRaises(
            collector.InvalidConfiguration,
            collector.BaseCollector.check_configuration, data)
