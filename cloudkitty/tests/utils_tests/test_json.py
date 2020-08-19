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
import decimal

from dateutil import tz

from cloudkitty import tests
from cloudkitty.utils import json


class JSONEncoderTest(tests.TestCase):

    def test_encode_decimal(self):
        obj = {'nb': decimal.Decimal(42)}
        self.assertEqual(json.dumps(obj), '{"nb": 42.0}')

    def test_encode_datetime(self):
        obj = {'date': datetime.datetime(2019, 1, 1, tzinfo=tz.tzutc())}
        self.assertEqual(json.dumps(obj),
                         '{"date": "2019-01-01T00:00:00+00:00"}')
