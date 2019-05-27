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
import collections
from datetime import datetime
import unittest

import mock

from cloudkitty.storage.v2 import influx
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
            influx.InfluxStorage._point_to_dataframe_entry(self.point), {
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
            influx.InfluxStorage._point_to_dataframe_entry(self.point), {
                'vol': {'unit': 'banana', 'qty': 42},
                'rating': {'price': 1.0},
                'groupby': {'a': ''},
                'metadata': {}
            }
        )


class TestInfluxClient(unittest.TestCase):

    def setUp(self):
        self.client = influx.InfluxClient()
        self._storage = influx.InfluxStorage()

    def test_get_filter_query(self):
        filters = collections.OrderedDict(
            (('str_filter', 'one'), ('float_filter', 2.0)))
        self.assertEqual(
            self.client._get_filter_query(filters),
            """ AND "str_filter"='one' AND "float_filter"=2.0"""
        )

    def test_get_filter_query_no_filters(self):
        self.assertEqual(self.client._get_filter_query({}), '')

    def test_delete_no_parameters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete()
        m.assert_called_once_with('DELETE FROM "dataframes";')

    def test_delete_begin_end(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(begin=datetime(2019, 1, 1),
                             end=datetime(2019, 1, 2))
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time >= '2019-01-01T00:00:00Z'"""
            """ AND time < '2019-01-02T00:00:00Z';""")

    def test_delete_begin_end_filters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(
            begin=datetime(2019, 1, 1), end=datetime(2019, 1, 2),
            filters={'project_id': 'foobar'})
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time >= '2019-01-01T00:00:00Z'"""
            """ AND time < '2019-01-02T00:00:00Z' AND "project_id"='foobar';"""
        )

    def test_delete_end_filters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(end=datetime(2019, 1, 2),
                             filters={'project_id': 'foobar'})
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time < '2019-01-02T00:00:00Z' """
            """AND "project_id"='foobar';""")

    def test_delete_begin_filters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(begin=datetime(2019, 1, 2),
                             filters={'project_id': 'foobar'})
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time >= '2019-01-02T00:00:00Z'"""
            """ AND "project_id"='foobar';""")

    def test_delete_begin(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(begin=datetime(2019, 1, 2))
        m.assert_called_once_with("""DELETE FROM "dataframes" WHERE """
                                  """time >= '2019-01-02T00:00:00Z';""")

    def test_delete_end(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(end=datetime(2019, 1, 2))
        m.assert_called_once_with("""DELETE FROM "dataframes" WHERE """
                                  """time < '2019-01-02T00:00:00Z';""")
