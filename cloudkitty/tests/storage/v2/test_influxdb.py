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
from cloudkitty.storage.v2.influx import InfluxStorage
from cloudkitty.tests import TestCase


class TestInfluxDBStorage(TestCase):

    def setUp(self):
        super(TestInfluxDBStorage, self).setUp()
        self.point = {
            'unit': 'banana',
            'qty': 42,
            'price': 1.0,
            'groupby': 'one|two',
            'metadata': '1|2',
            'one': '1',
            'two': '2',
            '1': 'one',
            '2': 'two',
        }

    def test_point_to_dataframe_entry_valid_point(self):
        self.assertEqual(
            InfluxStorage._point_to_dataframe_entry(self.point), {
                'vol': {'unit': 'banana', 'qty': 42},
                'rating': {'price': 1.0},
                'groupby': {'one': '1', 'two': '2'},
                'metadata': {'1': 'one', '2': 'two'},
            }
        )

    def test_point_to_dataframe_entry_invalid_groupby_metadata(self):
        self.point['groupby'] = 'a'
        self.point['metadata'] = None
        self.assertEqual(
            InfluxStorage._point_to_dataframe_entry(self.point), {
                'vol': {'unit': 'banana', 'qty': 42},
                'rating': {'price': 1.0},
                'groupby': {'a': ''},
                'metadata': {}
            }
        )
