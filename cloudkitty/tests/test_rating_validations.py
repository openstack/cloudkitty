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

from dateutil import tz
import webob.exc

from cloudkitty.rating.common.validations import fields
from cloudkitty import tests
from cloudkitty.utils import tz as tzutils

# Server-local time used by the tests: UTC+3, so results do not depend on
# the timezone of the machine running them.
LOCAL_TZ = tz.tzoffset('LOCAL', 3 * 3600)
UTC = datetime.timezone.utc
PLUS_4 = datetime.timezone(datetime.timedelta(hours=4))


class FakeResource(object):
    _wsme_attributes = []

    def __init__(self, start=None, end=None, name='rule'):
        self.start = start
        self.end = end
        self.name = name


class TestRatingRuleDatesValidation(tests.TestCase):

    def setUp(self):
        super().setUp()
        self.now = datetime.datetime(2030, 1, 1, 12, 0, 0)
        patcher = mock.patch.object(tzutils, '_LOCAL_TZ', LOCAL_TZ)
        patcher.start()
        self.addCleanup(patcher.stop)
        dt_patcher = mock.patch.object(fields, 'datetime')
        mock_dt = dt_patcher.start()
        self.addCleanup(dt_patcher.stop)
        mock_dt.datetime.now.return_value = self.now

    def test_aware_dates_converted_to_local_naive(self):
        res = FakeResource(
            start=datetime.datetime(2031, 1, 1, tzinfo=PLUS_4),
            end=datetime.datetime(2031, 1, 2, tzinfo=UTC))
        fields.validate_resource(res)
        self.assertEqual(datetime.datetime(2030, 12, 31, 23), res.start)
        self.assertEqual(datetime.datetime(2031, 1, 2, 3), res.end)

    def test_aware_start_in_past_is_bad_request(self):
        res = FakeResource(
            start=datetime.datetime(2020, 1, 1, tzinfo=PLUS_4))
        self.assertRaises(webob.exc.HTTPBadRequest,
                          fields.validate_resource, res)

    def test_update_running_rule_with_aware_future_end(self):
        current = FakeResource(start=datetime.datetime(2020, 1, 1))
        res = FakeResource(end=datetime.datetime(2031, 1, 1, tzinfo=UTC),
                           name=None)
        self.assertTrue(
            fields.validate_update_allowing_only_end_date(current, res))
        self.assertEqual(datetime.datetime(2031, 1, 1, 3), res.end)

    def test_naive_dates_unchanged(self):
        start = datetime.datetime(2031, 1, 1)
        end = datetime.datetime(2031, 1, 2)
        res = FakeResource(start=start, end=end)
        fields.validate_resource(res)
        self.assertEqual((start, end), (res.start, res.end))
