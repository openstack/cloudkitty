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
import unittest
from unittest import mock

from dateutil import tz
from oslo_utils import timeutils

from cloudkitty import utils
from cloudkitty.utils import tz as tzutils


class TestTZUtils(unittest.TestCase):

    def setUp(self):
        self.local_now = tzutils.localized_now()
        self.naive_now = utils.utcnow().replace(microsecond=0)

    def test_localized_now(self):
        self.assertEqual(
            self.local_now.astimezone(tz.tzutc()).replace(tzinfo=None),
            self.naive_now)
        self.assertIsNotNone(self.local_now.tzinfo)

    def test_local_to_utc_naive(self):
        naive_local = tzutils.local_to_utc(self.local_now, naive=True)
        naive_naive = tzutils.local_to_utc(self.naive_now, naive=True)
        self.assertIsNone(naive_local.tzinfo)
        self.assertIsNone(naive_naive.tzinfo)
        self.assertEqual(naive_local, naive_naive)

    def test_local_to_utc_not_naive(self):
        local = tzutils.local_to_utc(self.local_now)
        naive = tzutils.local_to_utc(self.naive_now)
        self.assertIsNotNone(local.tzinfo)
        self.assertIsNotNone(naive.tzinfo)
        self.assertEqual(local, naive)

    def test_utc_to_local(self):
        self.assertEqual(tzutils.utc_to_local(self.naive_now), self.local_now)

    def test_dt_from_iso(self):
        tester = '2019-06-06T16:30:54+02:00'
        tester_utc = '2019-06-06T14:30:54+00:00'

        dt = tzutils.dt_from_iso(tester)
        self.assertIsNotNone(dt.tzinfo)
        self.assertEqual(tzutils.dt_from_iso(tester, as_utc=True).isoformat(),
                         tester_utc)

    def _test_add_substract_delta(self, obj, tzone):
        delta = datetime.timedelta(seconds=3600)
        naive = obj.astimezone(tz.tzutc()).replace(tzinfo=None)

        self.assertEqual(
            tzutils.add_delta(obj, delta).astimezone(tzone),
            (naive + delta).replace(tzinfo=tz.tzutc()).astimezone(tzone),
        )
        self.assertEqual(
            tzutils.substract_delta(obj, delta).astimezone(tzone),
            (naive - delta).replace(tzinfo=tz.tzutc()).astimezone(tzone),
        )

    def test_add_substract_delta_summertime(self):
        tzone = tz.gettz('Europe/Paris')
        obj = datetime.datetime(2019, 3, 31, 1, tzinfo=tzone)
        self._test_add_substract_delta(obj, tzone)

    def test_add_substract_delta(self):
        tzone = tz.gettz('Europe/Paris')
        obj = datetime.datetime(2019, 1, 1, tzinfo=tzone)
        self._test_add_substract_delta(obj, tzone)

    def test_get_month_start_no_arg(self):
        naive_utc_now = timeutils.utcnow()
        naive_month_start = datetime.datetime(
            naive_utc_now.year, naive_utc_now.month, 1)
        month_start = tzutils.get_month_start()
        self.assertIsNotNone(month_start.tzinfo)
        self.assertEqual(
            naive_month_start,
            month_start.replace(tzinfo=None))

    def test_get_month_start_with_arg(self):
        param = datetime.datetime(2019, 1, 3, 4, 5)
        month_start = tzutils.get_month_start(param)
        self.assertIsNotNone(month_start.tzinfo)
        self.assertEqual(month_start.replace(tzinfo=None),
                         datetime.datetime(2019, 1, 1))

    def test_get_month_start_with_arg_naive(self):
        param = datetime.datetime(2019, 1, 3, 4, 5)
        month_start = tzutils.get_month_start(param, naive=True)
        self.assertIsNone(month_start.tzinfo)
        self.assertEqual(month_start, datetime.datetime(2019, 1, 1))

    def test_diff_seconds_positive_arg_naive_objects(self):
        one = datetime.datetime(2019, 1, 1, 1, 1, 30)
        two = datetime.datetime(2019, 1, 1, 1, 1)
        self.assertEqual(tzutils.diff_seconds(one, two), 30)

    def test_diff_seconds_negative_arg_naive_objects(self):
        one = datetime.datetime(2019, 1, 1, 1, 1, 30)
        two = datetime.datetime(2019, 1, 1, 1, 1)
        self.assertEqual(tzutils.diff_seconds(two, one), 30)

    def test_diff_seconds_positive_arg_aware_objects(self):
        one = datetime.datetime(2019, 1, 1, 1, 1, 30, tzinfo=tz.tzutc())
        two = datetime.datetime(2019, 1, 1, 1, 1, tzinfo=tz.tzutc())
        self.assertEqual(tzutils.diff_seconds(one, two), 30)

    def test_diff_seconds_negative_arg_aware_objects(self):
        one = datetime.datetime(2019, 1, 1, 1, 1, 30, tzinfo=tz.tzutc())
        two = datetime.datetime(2019, 1, 1, 1, 1, tzinfo=tz.tzutc())
        self.assertEqual(tzutils.diff_seconds(two, one), 30)

    def test_diff_seconds_negative_arg_aware_objects_on_summer_change(self):
        one = datetime.datetime(2019, 3, 31, 1,
                                tzinfo=tz.gettz('Europe/Paris'))
        two = datetime.datetime(2019, 3, 31, 3,
                                tzinfo=tz.gettz('Europe/Paris'))
        self.assertEqual(tzutils.diff_seconds(two, one), 3600)

    def test_cloudkitty_dt_from_ts_as_utc(self):
        ts = 1569902400
        dt = datetime.datetime(2019, 10, 1, 4, tzinfo=tz.tzutc())
        self.assertEqual(dt, tzutils.dt_from_ts(ts, as_utc=True))

    def test_cloudkitty_dt_from_ts_local_tz(self):
        ts = 1569902400
        timezone = tz.gettz('Europe/Paris')
        dt = datetime.datetime(2019, 10, 1, 6, tzinfo=timezone)
        with mock.patch.object(tzutils, '_LOCAL_TZ', new=timezone):
            self.assertEqual(dt, tzutils.dt_from_ts(ts))
