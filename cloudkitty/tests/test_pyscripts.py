# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
import decimal
import hashlib
from unittest import mock
import zlib

from oslo_utils import uuidutils

from cloudkitty import dataframe
from cloudkitty.rating import pyscripts
from cloudkitty.rating.pyscripts.db import api
from cloudkitty import tests

from dateutil import parser


FAKE_UUID = '6c1b8a30-797f-4b7e-ad66-9879b79059fb'
CK_RESOURCES_DATA = {
    "period": {
        "begin": "2014-10-01T00:00:00",
        "end": "2014-10-01T01:00:00"},
    "usage": {
        "instance_status": [
            dataframe.DataPoint(
                "instance", 1, 0,
                {"availability_zone": "nova",
                 "flavor": "m1.ultra",
                 "image_id": "f5600101-8fa2-4864-899e-ebcb7ed6b568",
                 "memory": "64",
                 "name": "prod1",
                 "project_id": "f266f30b11f246b589fd266f85eeec39",
                 "user_id": "55b3379b949243009ee96972fbf51ed1",
                 "vcpus": "1"
                 },
                {"farm": "prod"}),
            dataframe.DataPoint(
                "instance", 1, 0,
                {"availability_zone": "nova",
                 "flavor": "m1.not_so_ultra",
                 "image_id": "f5600101-8fa2-4864-899e-ebcb7ed6b568",
                 "memory": "64",
                 "name": "prod1",
                 "project_id": "f266f30b11f246b589fd266f85eeec39",
                 "user_id": "55b3379b949243009ee96972fbf51ed1",
                 "vcpus": "1"
                 },
                {"farm": "prod"})],
        "compute": [
            dataframe.DataPoint(
                "instance", 1, 0,
                {"availability_zone": "nova",
                 "flavor": "m1.nano",
                 "image_id": "f5600101-8fa2-4864-899e-ebcb7ed6b568",
                 "memory": "64",
                 "name": "prod1",
                 "project_id": "f266f30b11f246b589fd266f85eeec39",
                 "user_id": "55b3379b949243009ee96972fbf51ed1",
                 "vcpus": "1"
                 },
                {"farm": "prod"}),
            dataframe.DataPoint(
                "instance", 2, 0,
                {"availability_zone": "nova",
                 "flavor": "m1.tiny",
                 "image_id": "a41fba37-2429-4f15-aa00-b5bc4bf557bf",
                 "memory": "512",
                 "name": "dev1",
                 "project_id": "f266f30b11f246b589fd266f85eeec39",
                 "user_id": "55b3379b949243009ee96972fbf51ed1",
                 "vcpus": "1"
                 },
                {"farm": "dev"}),
            dataframe.DataPoint(
                "instance", 1, 0,
                {"availability_zone": "nova",
                 "flavor": "m1.nano",
                 "image_id": "a41fba37-2429-4f15-aa00-b5bc4bf557bf",
                 "memory": "64",
                 "name": "dev2",
                 "project_id": "f266f30b11f246b589fd266f85eeec39",
                 "user_id": "55b3379b949243009ee96972fbf51ed1",
                 "vcpus": "1"
                 },
                {"farm": "dev"}),
        ]
    }
}

TEST_CODE1 = 'a = 1'.encode('utf-8')
TEST_CODE1_CHECKSUM = hashlib.sha512(TEST_CODE1).hexdigest()
TEST_CODE2 = 'a = 0'.encode('utf-8')
TEST_CODE2_CHECKSUM = hashlib.sha512(TEST_CODE2).hexdigest()
TEST_CODE3 = 'if a == 1: raise Exception()'.encode('utf-8')
TEST_CODE3_CHECKSUM = hashlib.sha512(TEST_CODE3).hexdigest()

COMPLEX_POLICY1 = """
import decimal

usage_data = data['usage']
for service in usage_data.keys():
    if service == 'compute':
        all_points = usage_data.get(service, [])
        for resource in all_points:
            if resource['groupby'].get('flavor') == 'm1.nano':
                resource['rating'] = {
                    'price': decimal.Decimal(2.0)}
    if service == 'instance_status':
        all_points = usage_data.get(service, [])
        for resource in all_points:
            if resource['groupby'].get('flavor') == 'm1.ultra':
                resource['rating'] = {
                    'price': decimal.Decimal(
                        resource['groupby'].get(
                            'memory')) * decimal.Decimal(1.5)}
""".encode('utf-8')


DOCUMENTATION_RATING_POLICY = """
import decimal


# Price for each flavor. These are equivalent to hashmap field mappings.
flavors = {
    'm1.micro': decimal.Decimal(0.65),
    'm1.nano': decimal.Decimal(0.35),
    'm1.large': decimal.Decimal(2.67)
}

# Price per MB / GB for images and volumes. These are equivalent to
# hashmap service mappings.
image_mb_price = decimal.Decimal(0.002)
volume_gb_price = decimal.Decimal(0.35)

# These functions return the price of a service usage on a collect period.
# The price is always equivalent to the price per unit multiplied by
# the quantity.
def get_compute_price(item):
    flavor_name = item['groupby']['flavor']
    if not flavor_name in flavors:
        return 0
    else:
        return (decimal.Decimal(item['vol']['qty']) * flavors[flavor_name])

def get_image_price(item):
    if not item['vol']['qty']:
        return 0
    else:
        return decimal.Decimal(item['vol']['qty']) * image_mb_price


def get_volume_price(item):
    if not item['vol']['qty']:
        return 0
    else:
        return decimal.Decimal(item['vol']['qty']) * volume_gb_price

# Mapping each service to its price calculation function
services = {
    'compute': get_compute_price,
    'volume': get_volume_price,
    'image': get_image_price
}

def process(data):
    # The 'data' is a dictionary with the usage entries for each service for
    # each given period.
    usage_data = data['usage']

    for service_name, service_data in usage_data.items():
        # Do not calculate the price if the service has no
        # price calculation function
        if service_name in services.keys():
            # A service can have several items. For example,
            # each running instance is an item of the compute service
            for item in service_data:
                item['rating'] = {'price': services[service_name](item)}
    return data

# 'data' is passed as a global variable. The script is supposed to set the
# 'rating' element of each item in each service
data = process(data)
""".encode('utf-8')


class PyScriptsRatingTest(tests.TestCase):
    def setUp(self):
        super(PyScriptsRatingTest, self).setUp()
        self._tenant_id = 'f266f30b11f246b589fd266f85eeec39'
        self._db_api = pyscripts.PyScripts.db_api
        self._db_api.get_migration().upgrade('head')
        self._pyscripts = pyscripts.PyScripts(self._tenant_id)

        self.dataframe_for_tests = dataframe.DataFrame(
            parser.parse(CK_RESOURCES_DATA['period']['begin']),
            parser.parse(CK_RESOURCES_DATA['period']['end']),
            CK_RESOURCES_DATA['usage'])

    # Scripts tests
    @mock.patch.object(uuidutils, 'generate_uuid',
                       return_value=FAKE_UUID)
    def test_create_script(self, patch_generate_uuid):
        self._db_api.create_script('policy1', TEST_CODE1)
        scripts = self._db_api.list_scripts()
        self.assertEqual([FAKE_UUID], scripts)
        patch_generate_uuid.assert_called_once_with()

    def test_create_duplicate_script(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        self.assertRaises(api.ScriptAlreadyExists,
                          self._db_api.create_script,
                          'policy1',
                          TEST_CODE1)

    def test_get_script_by_uuid(self):
        expected = self._db_api.create_script('policy1', TEST_CODE1)
        actual = self._db_api.get_script(uuid=expected.script_id)
        self.assertEqual(expected.data, actual.data)

    def test_get_script_by_name(self):
        expected = self._db_api.create_script('policy1', TEST_CODE1)
        actual = self._db_api.get_script(expected.name)
        self.assertEqual(expected.data, actual.data)

    def test_get_script_without_parameters(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        self.assertRaises(
            ValueError,
            self._db_api.get_script)

    def test_delete_script_by_name(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        self._db_api.delete_script('policy1')
        scripts = self._db_api.list_scripts()
        self.assertEqual([], scripts)

    def test_delete_script_by_uuid(self):
        script_db = self._db_api.create_script('policy1', TEST_CODE1)
        self._db_api.delete_script(uuid=script_db.script_id)
        scripts = self._db_api.list_scripts()
        self.assertEqual([], scripts)

    def test_delete_script_without_parameters(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        self.assertRaises(
            ValueError,
            self._db_api.delete_script)

    def test_delete_unknown_script_by_name(self):
        self.assertRaises(api.NoSuchScript,
                          self._db_api.delete_script,
                          'dummy')

    def test_delete_unknown_script_by_uuid(self):
        self.assertRaises(
            api.NoSuchScript,
            self._db_api.delete_script,
            uuid='6e8de9fc-ee17-4b60-b81a-c9320e994e76')

    def test_update_script(self):
        script_db = self._db_api.create_script('policy1', TEST_CODE1)
        self._db_api.update_script(script_db.script_id, data=TEST_CODE2)
        actual = self._db_api.get_script(uuid=script_db.script_id)
        self.assertEqual(TEST_CODE2, actual.data)

    def test_update_script_uuid_disabled(self):
        expected = self._db_api.create_script('policy1', TEST_CODE1)
        self._db_api.update_script(expected.script_id,
                                   data=TEST_CODE2,
                                   script_id='42')
        actual = self._db_api.get_script(uuid=expected.script_id)
        self.assertEqual(expected.script_id, actual.script_id)

    def test_update_script_unknown_attribute(self):
        expected = self._db_api.create_script('policy1', TEST_CODE1)
        self.assertRaises(
            ValueError,
            self._db_api.update_script,
            expected.script_id,
            nonexistent=1)

    def test_empty_script_update(self):
        expected = self._db_api.create_script('policy1', TEST_CODE1)
        self.assertRaises(
            ValueError,
            self._db_api.update_script,
            expected.script_id)

    # Storage tests
    def test_compressed_data(self):
        data = TEST_CODE1
        self._db_api.create_script('policy1', data)
        script = self._db_api.get_script('policy1')
        expected = zlib.compress(data)
        self.assertEqual(expected, script._data)

    def test_on_the_fly_decompression(self):
        data = TEST_CODE1
        self._db_api.create_script('policy1', data)
        script = self._db_api.get_script('policy1')
        self.assertEqual(data, script.data)

    def test_script_repr(self):
        script_db = self._db_api.create_script('policy1', TEST_CODE1)
        self.assertEqual(
            '<PyScripts Script[{uuid}]: name={name}>'.format(
                uuid=script_db.script_id,
                name=script_db.name),
            str(script_db))

    # Checksum tests
    def test_validate_checksum(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        script = self._db_api.get_script('policy1')
        self.assertEqual(TEST_CODE1_CHECKSUM, script.checksum)

    def test_read_only_checksum(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        script = self._db_api.get_script('policy1')
        self.assertRaises(
            AttributeError,
            setattr,
            script,
            'checksum',
            'cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce4'
            '7d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e')

    def test_update_checksum(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        script = self._db_api.get_script('policy1')
        script = self._db_api.update_script(script.script_id, data=TEST_CODE2)
        self.assertEqual(TEST_CODE2_CHECKSUM, script.checksum)

    # Code exec tests
    def test_load_scripts(self):
        policy1_db = self._db_api.create_script('policy1', TEST_CODE1)
        policy2_db = self._db_api.create_script('policy2', TEST_CODE2)
        self._pyscripts.load_scripts_in_memory()
        self.assertIn(policy1_db.script_id, self._pyscripts._scripts)
        self.assertIn(policy2_db.script_id, self._pyscripts._scripts)

    def test_purge_old_scripts(self):
        policy1_db = self._db_api.create_script('policy1', TEST_CODE1)
        policy2_db = self._db_api.create_script('policy2', TEST_CODE2)
        self._pyscripts.reload_config()
        self.assertIn(policy1_db.script_id, self._pyscripts._scripts)
        self.assertIn(policy2_db.script_id, self._pyscripts._scripts)
        self._db_api.delete_script(uuid=policy1_db.script_id)
        self._pyscripts.reload_config()
        self.assertNotIn(policy1_db.script_id, self._pyscripts._scripts)
        self.assertIn(policy2_db.script_id, self._pyscripts._scripts)

    @mock.patch.object(uuidutils, 'generate_uuid',
                       return_value=FAKE_UUID)
    def test_valid_script_data_loaded(self, patch_generate_uuid):
        self._db_api.create_script('policy1', TEST_CODE1)
        self._pyscripts.load_scripts_in_memory()
        expected = {
            FAKE_UUID: {
                'code': compile(
                    TEST_CODE1,
                    '<PyScripts: {name}>'.format(name='policy1'),
                    'exec'),
                'checksum': TEST_CODE1_CHECKSUM,
                'name': 'policy1'
            }}
        self.assertEqual(expected, self._pyscripts._scripts)
        context = {'a': 0}
        exec(self._pyscripts._scripts[FAKE_UUID]['code'], context)  # nosec
        self.assertEqual(1, context['a'])

    def test_update_script_on_checksum_change(self):
        policy_db = self._db_api.create_script('policy1', TEST_CODE1)
        self._pyscripts.reload_config()
        self._db_api.update_script(policy_db.script_id, data=TEST_CODE2)
        self._pyscripts.reload_config()
        self.assertEqual(
            TEST_CODE2_CHECKSUM,
            self._pyscripts._scripts[policy_db.script_id]['checksum'])

    def test_exec_code_isolation(self):
        self._db_api.create_script('policy1', TEST_CODE1)
        self._db_api.create_script('policy2', TEST_CODE3)
        self._pyscripts.reload_config()

        self.assertEqual(2, len(self._pyscripts._scripts))
        self.assertRaises(NameError, self._pyscripts.process,
                          self.dataframe_for_tests)

    # Processing
    def test_process_rating(self):
        self._db_api.create_script('policy1', COMPLEX_POLICY1)
        self._pyscripts.reload_config()

        data_output = self._pyscripts.process(self.dataframe_for_tests)
        self.assertIsInstance(data_output, dataframe.DataFrame)

        dict_output = data_output.as_dict()
        for point in dict_output['usage']['compute']:
            if point['groupby'].get('flavor') == 'm1.nano':
                self.assertEqual(
                    decimal.Decimal('2'),  point['rating']['price'])
            else:
                self.assertEqual(
                    decimal.Decimal('0'), point['rating']['price'])
        for point in dict_output['usage']['instance_status']:
            if point['groupby'].get('flavor') == 'm1.ultra':
                self.assertEqual(
                    decimal.Decimal('96'),  point['rating']['price'])
            else:
                self.assertEqual(
                    decimal.Decimal('0'), point['rating']['price'])

    # Processing
    def test_process_rating_with_documentation_rules(self):
        self._db_api.create_script('policy1', DOCUMENTATION_RATING_POLICY)
        self._pyscripts.reload_config()

        dataframe_for_tests = copy.deepcopy(self.dataframe_for_tests)
        dataframe_for_tests.add_point(
            dataframe.DataPoint("GB", 5, 0, {"tag": "A"}, {}), "image")
        dataframe_for_tests.add_point(
            dataframe.DataPoint("GB", 15, 0, {"tag": "B"}, {}), "image")

        dataframe_for_tests.add_point(
            dataframe.DataPoint("GB", 500, 0, {"tag": "D"}, {}), "volume")
        dataframe_for_tests.add_point(
            dataframe.DataPoint("GB", 80, 0, {"tag": "E"}, {}), "volume")

        data_output = self._pyscripts.process(dataframe_for_tests)
        self.assertIsInstance(data_output, dataframe.DataFrame)

        dict_output = data_output.as_dict()
        for point in dict_output['usage']['compute']:
            if point['groupby'].get('flavor') == 'm1.nano':
                self.assertEqual(
                    decimal.Decimal('0.3499999999999999777955395075'),
                    point['rating']['price'])
            else:
                self.assertEqual(
                    decimal.Decimal('0'), point['rating']['price'])
        for point in dict_output['usage']['instance_status']:
            if point['groupby'].get('flavor') == 'm1.ultra':
                self.assertEqual(
                    decimal.Decimal('0'),  point['rating']['price'])
            else:
                self.assertEqual(
                    decimal.Decimal('0'), point['rating']['price'])

        for point in dict_output['usage']['image']:
            if point['groupby'].get('tag') == 'A':
                self.assertEqual(
                    decimal.Decimal('0.01000000000000000020816681712'),
                    point['rating']['price'])
            else:
                self.assertEqual(
                    decimal.Decimal('0.03000000000000000062450045135'),
                    point['rating']['price'])

        for point in dict_output['usage']['volume']:
            if point['groupby'].get('tag') == 'D':
                self.assertEqual(
                    decimal.Decimal('174.9999999999999888977697537'),
                    point['rating']['price'])
            else:
                self.assertEqual(
                    decimal.Decimal('27.99999999999999822364316060'),
                    point['rating']['price'])
