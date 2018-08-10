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
# @author: Stéphane Albert
#
import copy
import decimal
import hashlib
import testtools
import zlib

import mock
from oslo_utils import uuidutils
import six

from cloudkitty.rating import pyscripts
from cloudkitty.rating.pyscripts.db import api
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test


FAKE_UUID = '6c1b8a30-797f-4b7e-ad66-9879b79059fb'
CK_RESOURCES_DATA = [{
    "period": {
        "begin": "2014-10-01T00:00:00",
        "end": "2014-10-01T01:00:00"},
    "usage": {
        "compute": [
            {
                "desc": {
                    "availability_zone": "nova",
                    "flavor": "m1.nano",
                    "image_id": "f5600101-8fa2-4864-899e-ebcb7ed6b568",
                    "memory": "64",
                    "metadata": {
                        "farm": "prod"},
                    "name": "prod1",
                    "project_id": "f266f30b11f246b589fd266f85eeec39",
                    "user_id": "55b3379b949243009ee96972fbf51ed1",
                    "vcpus": "1"},
                "vol": {
                    "qty": 1,
                    "unit": "instance"}
            },
            {
                "desc": {
                    "availability_zone": "nova",
                    "flavor": "m1.tiny",
                    "image_id": "a41fba37-2429-4f15-aa00-b5bc4bf557bf",
                    "memory": "512",
                    "metadata": {
                        "farm": "dev"},
                    "name": "dev1",
                    "project_id": "f266f30b11f246b589fd266f85eeec39",
                    "user_id": "55b3379b949243009ee96972fbf51ed1",
                    "vcpus": "1"},
                "vol": {
                    "qty": 2,
                    "unit": "instance"}},
            {
                "desc": {
                    "availability_zone": "nova",
                    "flavor": "m1.nano",
                    "image_id": "a41fba37-2429-4f15-aa00-b5bc4bf557bf",
                    "memory": "64",
                    "metadata": {
                        "farm": "dev"},
                    "name": "dev2",
                    "project_id": "f266f30b11f246b589fd266f85eeec39",
                    "user_id": "55b3379b949243009ee96972fbf51ed1",
                    "vcpus": "1"},
                "vol": {
                    "qty": 1,
                    "unit": "instance"}}]}}]

TEST_CODE1 = 'a = 1'.encode('utf-8')
TEST_CODE1_CHECKSUM = hashlib.sha1(TEST_CODE1).hexdigest()
TEST_CODE2 = 'a = 0'.encode('utf-8')
TEST_CODE2_CHECKSUM = hashlib.sha1(TEST_CODE2).hexdigest()
TEST_CODE3 = 'if a == 1: raise Exception()'.encode('utf-8')
TEST_CODE3_CHECKSUM = hashlib.sha1(TEST_CODE3).hexdigest()

COMPLEX_POLICY1 = """
import decimal


for period in data:
    for service, resources in period['usage'].items():
        if service == 'compute':
            for resource in resources:
                if resource['desc'].get('flavor') == 'm1.nano':
                    resource['rating'] = {
                        'price': decimal.Decimal(1.0)}
""".encode('utf-8')


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class PyScriptsRatingTest(tests.TestCase):
    def setUp(self):
        super(PyScriptsRatingTest, self).setUp()
        self._tenant_id = 'f266f30b11f246b589fd266f85eeec39'
        self._db_api = pyscripts.PyScripts.db_api
        self._db_api.get_migration().upgrade('head')
        self._pyscripts = pyscripts.PyScripts(self._tenant_id)

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
            six.text_type(script_db))

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
            'da39a3ee5e6b4b0d3255bfef95601890afd80709')

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
        exec(self._pyscripts._scripts[FAKE_UUID]['code'], context)
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
        self.assertRaises(NameError, self._pyscripts.process, {})

    # Processing
    def test_process_rating(self):
        self._db_api.create_script('policy1', COMPLEX_POLICY1)
        self._pyscripts.reload_config()
        actual_data = copy.deepcopy(CK_RESOURCES_DATA)
        expected_data = copy.deepcopy(CK_RESOURCES_DATA)
        compute_list = expected_data[0]['usage']['compute']
        compute_list[0]['rating'] = {'price': decimal.Decimal('1')}
        compute_list[2]['rating'] = {'price': decimal.Decimal('1')}
        self._pyscripts.process(actual_data)
        self.assertEqual(expected_data, actual_data)
