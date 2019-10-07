# Copyright 2019 Objectif Libre
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
import datetime
from unittest import mock

from cloudkitty.collector import monasca as mon_collector
from cloudkitty import tests


class MonascaCollectorTest(tests.TestCase):

    def setUp(self):
        super(MonascaCollectorTest, self).setUp()
        self.conf.set_override('collector', 'monasca', 'collect')
        conf = {
            'metrics': {
                'metric_one': {
                    'unit': 'GiB',
                    'groupby': ['project_id'],
                    'extra_args': {
                        'aggregation_method': 'max',
                    },
                },
                'metric_two': {
                    'unit': 'MiB',
                    'groupby': ['project_id'],
                    'extra_args': {
                        'aggregation_method': 'max',
                        'forced_project_id': 'project_x'
                    },
                },
            }
        }
        with mock.patch(
                'cloudkitty.common.monasca_client.'
                'get_monasca_endpoint',
                return_value='http://noop'):
            self.collector = mon_collector.MonascaCollector(
                period=3600,
                conf=conf,
            )

    def test_fetch_measures_kwargs_no_forced_project(self):
        with mock.patch.object(self.collector._conn.metrics,
                               'list_statistics') as m:
            start = datetime.datetime(2019, 1, 1)
            end = datetime.datetime(2019, 1, 1, 1)
            self.collector._fetch_measures(
                'metric_one',
                start,
                end,
            )
            m.assert_called_once_with(
                name='metric_one',
                merge_metrics=True,
                dimensions={},
                start_time=start,
                end_time=end,
                period=3600,
                statistics='max',
                group_by=['project_id', 'resource_id'],
            )

    def test_fetch_measures_kwargs_with_forced_project(self):
        with mock.patch.object(self.collector._conn.metrics,
                               'list_statistics') as m:
            start = datetime.datetime(2019, 1, 1)
            end = datetime.datetime(2019, 1, 1, 1)
            self.collector._fetch_measures(
                'metric_two',
                start,
                end,
            )
            m.assert_called_once_with(
                name='metric_two',
                merge_metrics=True,
                dimensions={},
                start_time=start,
                end_time=end,
                period=3600,
                statistics='max',
                group_by=['project_id', 'resource_id'],
                tenant_id='project_x',
            )
