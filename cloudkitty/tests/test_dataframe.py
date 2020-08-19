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
import copy
import datetime
import decimal
import unittest

from dateutil import tz
from werkzeug import datastructures

from cloudkitty import dataframe
from cloudkitty.utils import json


class TestDataPoint(unittest.TestCase):

    default_params = {
        'qty': 0,
        'price': 0,
        'unit': None,
        'groupby': {},
        'metadata': {},
    }

    def test_create_empty_datapoint(self):
        point = dataframe.DataPoint(**self.default_params)
        self.assertEqual(point.qty, decimal.Decimal(0))
        self.assertEqual(point.price, decimal.Decimal(0))
        self.assertEqual(point.unit, "undefined")
        self.assertEqual(point.groupby, {})

    def test_readonly_attrs(self):
        point = dataframe.DataPoint(**self.default_params)
        for attr in ("qty", "price", "unit"):
            self.assertRaises(AttributeError, setattr, point, attr, 'x')

    def test_properties(self):
        params = copy.deepcopy(self.default_params)
        groupby = {"group_one": "one", "group_two": "two"}
        metadata = {"meta_one": "one", "meta_two": "two"}
        params.update({'groupby': groupby, 'metadata': metadata})
        point = dataframe.DataPoint(**params)
        self.assertEqual(point.groupby, groupby)
        self.assertEqual(point.metadata, metadata)

    def test_as_dict_mutable_standard(self):
        self.assertEqual(
            dataframe.DataPoint(
                **self.default_params).as_dict(mutable=True),
            {
                "vol": {"unit": "undefined", "qty": decimal.Decimal(0)},
                "rating": {"price": decimal.Decimal(0)},
                "groupby": {},
                "metadata": {},
            }
        )

    def test_as_dict_mutable_legacy(self):
        self.assertEqual(
            dataframe.DataPoint(**self.default_params).as_dict(
                legacy=True, mutable=True),
            {
                "vol": {"unit": "undefined", "qty": decimal.Decimal(0)},
                "rating": {"price": decimal.Decimal(0)},
                "desc": {},
            }
        )

    def test_as_dict_immutable(self):
        point_dict = dataframe.DataPoint(**self.default_params).as_dict()
        self.assertIsInstance(point_dict, datastructures.ImmutableDict)
        self.assertEqual(dict(point_dict), {
            "vol": {"unit": "undefined", "qty": decimal.Decimal(0)},
            "rating": {"price": decimal.Decimal(0)},
            "groupby": {},
            "metadata": {},
        })

    def test_json_standard(self):
        self.assertEqual(
            json.loads(dataframe.DataPoint(**self.default_params).json()), {
                "vol": {"unit": "undefined", "qty": decimal.Decimal(0)},
                "rating": {"price": decimal.Decimal(0)},
                "groupby": {},
                "metadata": {},
            }
        )

    def test_json_legacy(self):
        self.assertEqual(
            json.loads(dataframe.DataPoint(
                **self.default_params).json(legacy=True)),
            {
                "vol": {"unit": "undefined", "qty": decimal.Decimal(0)},
                "rating": {"price": decimal.Decimal(0)},
                "desc": {},
            }
        )

    def test_from_dict_valid_dict(self):
        self.assertEqual(
            dataframe.DataPoint(
                unit="amazing_unit",
                qty=3,
                price=0,
                groupby={"g_one": "one", "g_two": "two"},
                metadata={"m_one": "one", "m_two": "two"},
            ).as_dict(),
            dataframe.DataPoint.from_dict({
                "vol": {"unit": "amazing_unit", "qty": 3},
                "groupby": {"g_one": "one", "g_two": "two"},
                "metadata": {"m_one": "one", "m_two": "two"},
            }).as_dict(),
        )

    def test_from_dict_invalid(self):
        invalid = {
            "vol": {},
            "desc": {"a": "b"},
        }
        self.assertRaises(ValueError, dataframe.DataPoint.from_dict, invalid)

    def test_set_price(self):
        point = dataframe.DataPoint(**self.default_params)
        self.assertEqual(point.price, decimal.Decimal(0))
        self.assertEqual(point.set_price(42).price, decimal.Decimal(42))
        self.assertEqual(point.set_price(1337).price, decimal.Decimal(1337))

    def test_desc(self):
        params = copy.deepcopy(self.default_params)
        params['groupby'] = {'group_one': 'one', 'group_two': 'two'}
        params['metadata'] = {'meta_one': 'one', 'meta_two': 'two'}
        point = dataframe.DataPoint(**params)
        self.assertEqual(point.desc, {
            'group_one': 'one',
            'group_two': 'two',
            'meta_one': 'one',
            'meta_two': 'two',
        })


class TestDataFrame(unittest.TestCase):

    def test_dataframe_add_points(self):
        start = datetime.datetime(2019, 3, 4, 1, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 3, 4, 2, tzinfo=tz.tzutc())
        df = dataframe.DataFrame(start=start, end=end)
        a_points = [dataframe.DataPoint(**TestDataPoint.default_params)
                    for _ in range(2)]
        b_points = [dataframe.DataPoint(**TestDataPoint.default_params)
                    for _ in range(4)]

        df.add_point(a_points[0], 'service_a')
        df.add_points(a_points[1:], 'service_a')
        df.add_points(b_points[:2], 'service_b')
        df.add_points(b_points[2:3], 'service_b')
        df.add_point(b_points[3], 'service_b')

        self.assertEqual(dict(df.as_dict()), {
            'period': {'begin': start, 'end': end},
            'usage': {
                'service_a': [
                    dataframe.DataPoint(
                        **TestDataPoint.default_params).as_dict()
                    for _ in range(2)],
                'service_b': [
                    dataframe.DataPoint(
                        **TestDataPoint.default_params).as_dict()
                    for _ in range(4)],
            }
        })

    def test_properties(self):
        start = datetime.datetime(2019, 6, 1, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 6, 1, 1, tzinfo=tz.tzutc())
        df = dataframe.DataFrame(start=start, end=end)
        self.assertEqual(df.start, start)
        self.assertEqual(df.end, end)

    def test_json(self):
        start = datetime.datetime(2019, 3, 4, 1, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 3, 4, 2, tzinfo=tz.tzutc())
        df = dataframe.DataFrame(start=start, end=end)
        a_points = [dataframe.DataPoint(**TestDataPoint.default_params)
                    for _ in range(2)]
        b_points = [dataframe.DataPoint(**TestDataPoint.default_params)
                    for _ in range(4)]
        df.add_points(a_points, 'service_a')
        df.add_points(b_points, 'service_b')

        self.maxDiff = None
        self.assertEqual(json.loads(df.json()), json.loads(json.dumps({
            'period': {'begin': start.isoformat(),
                       'end': end.isoformat()},
            'usage': {
                'service_a': [
                    dataframe.DataPoint(
                        **TestDataPoint.default_params).as_dict()
                    for _ in range(2)],
                'service_b': [
                    dataframe.DataPoint(
                        **TestDataPoint.default_params).as_dict()
                    for _ in range(4)],
            }
        })))

    def test_from_dict_valid_dict(self):
        start = datetime.datetime(2019, 1, 2, 12, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 1, 2, 13, tzinfo=tz.tzutc())
        point = dataframe.DataPoint(
            'unit', 0, 0, {'g_one': 'one'}, {'m_two': 'two'})
        usage = {'metric_x': [point]}
        dict_usage = {'metric_x': [point.as_dict(mutable=True)]}
        self.assertEqual(
            dataframe.DataFrame(start, end, usage).as_dict(),
            dataframe.DataFrame.from_dict({
                'period': {'begin': start, 'end': end},
                'usage': dict_usage,
            }).as_dict(),
        )

    def test_from_dict_valid_dict_date_as_str(self):
        start = datetime.datetime(2019, 1, 2, 12, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 1, 2, 13, tzinfo=tz.tzutc())
        point = dataframe.DataPoint(
            'unit', 0, 0, {'g_one': 'one'}, {'m_two': 'two'})
        usage = {'metric_x': [point]}
        dict_usage = {'metric_x': [point.as_dict(mutable=True)]}
        self.assertEqual(
            dataframe.DataFrame(start, end, usage).as_dict(),
            dataframe.DataFrame.from_dict({
                'period': {'begin': start.isoformat(), 'end': end.isoformat()},
                'usage': dict_usage,
            }).as_dict(),
        )

    def test_from_dict_invalid_dict(self):
        self.assertRaises(
            ValueError, dataframe.DataFrame.from_dict, {'usage': None})

    def test_repr(self):
        start = datetime.datetime(2019, 3, 4, 1, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 3, 4, 2, tzinfo=tz.tzutc())
        df = dataframe.DataFrame(start=start, end=end)
        points = [dataframe.DataPoint(**TestDataPoint.default_params)
                  for _ in range(4)]
        df.add_points(points, 'metric_x')
        self.assertEqual(str(df), "DataFrame(metrics=[metric_x])")
        df.add_points(points, 'metric_y')
        self.assertEqual(str(df), "DataFrame(metrics=[metric_x,metric_y])")

    def test_iterpoints(self):
        start = datetime.datetime(2019, 3, 4, 1, tzinfo=tz.tzutc())
        end = datetime.datetime(2019, 3, 4, 2, tzinfo=tz.tzutc())
        df = dataframe.DataFrame(start=start, end=end)
        points = [dataframe.DataPoint(**TestDataPoint.default_params)
                  for _ in range(4)]
        df.add_points(points, 'metric_x')
        expected = [
            ('metric_x', dataframe.DataPoint(**TestDataPoint.default_params))
            for _ in range(4)]
        self.assertEqual(list(df.iterpoints()), expected)
