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
import copy
from datetime import datetime
from datetime import timedelta
import unittest
from unittest import mock

from dateutil import tz

from cloudkitty import dataframe
from cloudkitty.storage.v2 import influx
from cloudkitty.tests import TestCase
from cloudkitty.utils import tz as tzutils


class TestInfluxDBStorage(TestCase):

    def setUp(self):
        super(TestInfluxDBStorage, self).setUp()
        self.point = {
            'type': 'amazing_type',
            'unit': 'banana',
            'qty': 42,
            'price': 1.0,
            'groupby': 'one|two',
            'metadata': '1|2',
            'one': '1',
            'two': '2',
            '1': 'one',
            '2': 'two',
            'time': datetime(2019, 1, 1, tzinfo=tz.tzutc()).isoformat(),
        }

    def test_point_to_dataframe_entry_valid_point(self):
        self.assertEqual(
            influx.InfluxStorage._point_to_dataframe_entry(self.point),
            dataframe.DataPoint(
                'banana',
                42,
                1,
                {'one': '1', 'two': '2'},
                {'1': 'one', '2': 'two'},
            ),
        )

    def test_point_to_dataframe_entry_invalid_groupby_metadata(self):
        point = copy.deepcopy(self.point)
        point['groupby'] = 'a'
        point['metadata'] = None
        self.assertEqual(
            influx.InfluxStorage._point_to_dataframe_entry(point),
            dataframe.DataPoint(
                'banana',
                42,
                1,
                {'a': ''},
                {},
            ),
        )

    def test_build_dataframes_differenciates_periods(self):
        points = [copy.deepcopy(self.point) for _ in range(3)]
        for idx, point in enumerate(points):
            point[influx.PERIOD_FIELD_NAME] = 100 * (idx + 1)

        dataframes = influx.InfluxStorage()._build_dataframes(points)
        self.assertEqual(len(dataframes), 3)

        for idx, frame in enumerate(dataframes):
            self.assertEqual(
                frame.start, datetime(2019, 1, 1, tzinfo=tz.tzutc()))
            delta = timedelta(seconds=(idx + 1) * 100)
            self.assertEqual(frame.end,
                             datetime(2019, 1, 1, tzinfo=tz.tzutc()) + delta)
            typelist = list(frame.itertypes())
            self.assertEqual(len(typelist), 1)
            type_, points = typelist[0]
            self.assertEqual(len(points), 1)
            self.assertEqual(type_, 'amazing_type')


class FakeResultSet(object):
    def __init__(self, points=[], items=[]):
        self._points = points
        self._items = items

    def get_points(self):
        return self._points

    def items(self):
        return self._items


class TestInfluxClient(unittest.TestCase):
    def setUp(self):
        self.period_begin = tzutils.local_to_utc(
            tzutils.get_month_start()).isoformat()
        self.period_end = tzutils.local_to_utc(
            tzutils.get_next_month()).isoformat()
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

    def test_retrieve_format_with_pagination(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        m.return_value = (FakeResultSet(), FakeResultSet())

        self._storage.retrieve()
        m.assert_called_once_with(
            "SELECT COUNT(groupby) FROM \"dataframes\""
            " WHERE time >= '{0}'"
            " AND time < '{1}';"
            "SELECT * FROM \"dataframes\""
            " WHERE time >= '{0}'"
            " AND time < '{1}'"
            " LIMIT 1000 OFFSET 0;".format(
                self.period_begin, self.period_end,
            ))

    def test_retrieve_format_with_types(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        m.return_value = (FakeResultSet(), FakeResultSet())

        self._storage.retrieve(metric_types=['foo', 'bar'])
        m.assert_called_once_with(
            "SELECT COUNT(groupby) FROM \"dataframes\""
            " WHERE time >= '{0}'"
            " AND time < '{1}'"
            " AND (type='foo' OR type='bar');"
            "SELECT * FROM \"dataframes\""
            " WHERE time >= '{0}'"
            " AND time < '{1}'"
            " AND (type='foo' OR type='bar')"
            " LIMIT 1000 OFFSET 0;".format(
                self.period_begin, self.period_end,
            ))

    def test_delete_no_parameters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete()
        m.assert_called_once_with('DELETE FROM "dataframes";')

    def test_delete_begin_end(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(begin=datetime(2019, 1, 1),
                             end=datetime(2019, 1, 2))
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time >= '2019-01-01T00:00:00'"""
            """ AND time < '2019-01-02T00:00:00';""")

    def test_delete_begin_end_filters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(
            begin=datetime(2019, 1, 1), end=datetime(2019, 1, 2),
            filters={'project_id': 'foobar'})
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time >= '2019-01-01T00:00:00'"""
            """ AND time < '2019-01-02T00:00:00' AND "project_id"='foobar';"""
        )

    def test_delete_end_filters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(end=datetime(2019, 1, 2),
                             filters={'project_id': 'foobar'})
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time < '2019-01-02T00:00:00' """
            """AND "project_id"='foobar';""")

    def test_delete_begin_filters(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(begin=datetime(2019, 1, 2),
                             filters={'project_id': 'foobar'})
        m.assert_called_once_with(
            """DELETE FROM "dataframes" WHERE time >= '2019-01-02T00:00:00'"""
            """ AND "project_id"='foobar';""")

    def test_delete_begin(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(begin=datetime(2019, 1, 2))
        m.assert_called_once_with("""DELETE FROM "dataframes" WHERE """
                                  """time >= '2019-01-02T00:00:00';""")

    def test_delete_end(self):
        self._storage._conn._conn.query = m = mock.MagicMock()
        self._storage.delete(end=datetime(2019, 1, 2))
        m.assert_called_once_with("""DELETE FROM "dataframes" WHERE """
                                  """time < '2019-01-02T00:00:00';""")
