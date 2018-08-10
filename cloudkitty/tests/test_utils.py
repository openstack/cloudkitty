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
import datetime
import decimal
import fractions
import itertools
import testtools
import unittest

import mock
from oslo_utils import timeutils

from cloudkitty.tests.samples import DEFAULT_METRICS_CONF
from cloudkitty.tests.utils import is_functional_test
from cloudkitty import utils as ck_utils


def iso2dt(iso_str):
    return timeutils.parse_isotime(iso_str)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class UtilsTimeCalculationsTest(unittest.TestCase):
    def setUp(self):
        self.date_ts = 1416219015
        self.date_iso = '2014-11-17T10:10:15Z'
        self.date_params = {'year': 2014,
                            'month': 11,
                            'day': 17,
                            'hour': 10,
                            'minute': 10,
                            'second': 15}
        self.date_tz_params = {'year': 2014,
                               'month': 10,
                               'day': 26,
                               'hour': 2,
                               'minute': 00,
                               'second': 00}

    def test_dt2ts(self):
        date = datetime.datetime(**self.date_params)
        trans_ts = ck_utils.dt2ts(date)
        self.assertEqual(self.date_ts, trans_ts)

    def test_iso2dt(self):
        date = datetime.datetime(**self.date_params)
        trans_dt = ck_utils.iso2dt(self.date_iso)
        self.assertEqual(date, trans_dt)

    def test_ts2iso(self):
        trans_iso = ck_utils.ts2iso(self.date_ts)
        self.assertEqual(self.date_iso, trans_iso)

    def test_dt2iso(self):
        date = datetime.datetime(**self.date_params)
        trans_iso = ck_utils.dt2iso(date)
        self.assertEqual(self.date_iso, trans_iso)

    @mock.patch.object(ck_utils, 'utcnow',
                       return_value=iso2dt('2014-01-31T00:00:00Z'))
    def test_month_start_without_dt(self, patch_utcnow_mock):
        date = datetime.datetime(2014, 1, 1)
        trans_dt = ck_utils.get_month_start()
        self.assertEqual(date, trans_dt)
        patch_utcnow_mock.assert_called_once_with()

    @mock.patch.object(ck_utils, 'utcnow',
                       return_value=iso2dt('2014-01-15T00:00:00Z'))
    def test_month_end_without_dt(self, patch_utcnow_mock):
        date = datetime.datetime(2014, 1, 31)
        trans_dt = ck_utils.get_month_end()
        self.assertEqual(date, trans_dt)
        patch_utcnow_mock.assert_called_once_with()

    @mock.patch.object(ck_utils, 'utcnow',
                       return_value=iso2dt('2014-01-31T00:00:00Z'))
    def test_get_last_month_without_dt(self, patch_utcnow_mock):
        date = datetime.datetime(2013, 12, 1)
        trans_dt = ck_utils.get_last_month()
        self.assertEqual(date, trans_dt)
        patch_utcnow_mock.assert_called_once_with()

    @mock.patch.object(ck_utils, 'utcnow',
                       return_value=iso2dt('2014-01-31T00:00:00Z'))
    def test_get_next_month_without_dt(self, patch_utcnow_mock):
        date = datetime.datetime(2014, 2, 1)
        trans_dt = ck_utils.get_next_month()
        self.assertEqual(date, trans_dt)
        patch_utcnow_mock.assert_called_once_with()

    def test_get_last_month_leap(self):
        base_date = datetime.datetime(2016, 3, 31)
        date = datetime.datetime(2016, 2, 1)
        trans_dt = ck_utils.get_last_month(base_date)
        self.assertEqual(date, trans_dt)

    def test_get_next_month_leap(self):
        base_date = datetime.datetime(2016, 1, 31)
        date = datetime.datetime(2016, 2, 1)
        trans_dt = ck_utils.get_next_month(base_date)
        self.assertEqual(date, trans_dt)

    def test_add_month_leap(self):
        base_date = datetime.datetime(2016, 1, 31)
        date = datetime.datetime(2016, 3, 3)
        trans_dt = ck_utils.add_month(base_date, False)
        self.assertEqual(date, trans_dt)

    def test_add_month_keep_leap(self):
        base_date = datetime.datetime(2016, 1, 31)
        date = datetime.datetime(2016, 2, 29)
        trans_dt = ck_utils.add_month(base_date)
        self.assertEqual(date, trans_dt)

    def test_sub_month_leap(self):
        base_date = datetime.datetime(2016, 3, 31)
        date = datetime.datetime(2016, 3, 3)
        trans_dt = ck_utils.sub_month(base_date, False)
        self.assertEqual(date, trans_dt)

    def test_sub_month_keep_leap(self):
        base_date = datetime.datetime(2016, 3, 31)
        date = datetime.datetime(2016, 2, 29)
        trans_dt = ck_utils.sub_month(base_date)
        self.assertEqual(date, trans_dt)

    def test_load_timestamp(self):
        calc_dt = ck_utils.iso2dt(self.date_iso)
        check_dt = ck_utils.ts2dt(self.date_ts)
        self.assertEqual(calc_dt, check_dt)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class ConvertUnitTest(unittest.TestCase):
    """Class testing the convert_unit and num2decimal function"""
    possible_args = [
        None,  # Use default arg
        '2/3',
        decimal.Decimal(1.23),
        '1.23',
        2,
        '2',
        2.3,
    ]

    def test_arg_types(self):
        """Test function with several arg combinations of different types"""
        for fac, off in itertools.product(self.possible_args, repeat=2):
            factor = fac if fac else 1
            offset = off if off else 0
            ck_utils.convert_unit(10, factor, offset)

    def test_str_str_str(self):
        result = ck_utils.convert_unit('1/2', '1/2', '1/2')
        self.assertEqual(result, decimal.Decimal(0.5 * 0.5 + 0.5))

    def test_str_float_float(self):
        result = ck_utils.convert_unit('1/2', 0.5, 0.5)
        self.assertEqual(result, decimal.Decimal(0.5 * 0.5 + 0.5))

    def test_convert_str_float(self):
        result = ck_utils.num2decimal('2.0')
        self.assertEqual(result, decimal.Decimal(2.0))

    def test_convert_str_int(self):
        result = ck_utils.num2decimal('2')
        self.assertEqual(result, decimal.Decimal(2))

    def test_convert_str_fraction(self):
        result = ck_utils.num2decimal('2/3')
        self.assertEqual(result, decimal.Decimal(2.0 / 3))

    def test_convert_fraction(self):
        result = ck_utils.num2decimal(fractions.Fraction(1, 2))
        self.assertEqual(result, decimal.Decimal(1.0 / 2))

    def test_convert_float(self):
        result = ck_utils.num2decimal(0.5)
        self.assertEqual(result, decimal.Decimal(0.5))

    def test_convert_int(self):
        result = ck_utils.num2decimal(2)
        self.assertEqual(result, decimal.Decimal(2))

    def test_convert_decimal(self):
        result = ck_utils.num2decimal(decimal.Decimal(2))
        self.assertEqual(result, decimal.Decimal(2))


def load_conf(*args):
    return DEFAULT_METRICS_CONF
