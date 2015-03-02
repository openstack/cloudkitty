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
import decimal

import mock
from oslo.utils import uuidutils

from cloudkitty.billing import hash
from cloudkitty.billing.hash.db import api
from cloudkitty import tests

TEST_TS = 1388577600
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
                    "qty": 1,
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


class HashMapRatingTest(tests.TestCase):
    def setUp(self):
        super(HashMapRatingTest, self).setUp()
        self._tenant_id = 'f266f30b11f246b589fd266f85eeec39'
        self._db_api = hash.HashMap.db_api
        self._db_api.get_migration().upgrade('head')
        self._hash = hash.HashMap(self._tenant_id)

    # Group tests
    @mock.patch.object(uuidutils, 'generate_uuid',
                       return_value=FAKE_UUID)
    def test_create_group(self, patch_generate_uuid):
        self._db_api.create_group('test_group')
        groups = self._db_api.list_groups()
        self.assertEqual([FAKE_UUID], groups)
        patch_generate_uuid.assert_called_once()

    def test_create_duplicate_group(self):
        self._db_api.create_group('test_group')
        self.assertRaises(api.GroupAlreadyExists,
                          self._db_api.create_group,
                          'test_group')

    def test_delete_group(self):
        group_db = self._db_api.create_group('test_group')
        self._db_api.delete_group(group_db.group_id)
        groups = self._db_api.list_groups()
        self.assertEqual([], groups)

    def test_delete_unknown_group(self):
        self.assertRaises(api.NoSuchGroup,
                          self._db_api.delete_group,
                          uuidutils.generate_uuid())

    def test_recursive_delete_group(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        group_db = self._db_api.create_group('test_group')
        self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        self._db_api.delete_group(group_db.group_id)
        mappings = self._db_api.list_mappings(field_uuid=field_db.field_id)
        self.assertEqual([], mappings)
        groups = self._db_api.list_groups()
        self.assertEqual([], groups)

    def test_non_recursive_delete_group(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        group_db = self._db_api.create_group('test_group')
        mapping_db = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        self._db_api.delete_group(group_db.group_id, False)
        mappings = self._db_api.list_mappings(field_uuid=field_db.field_id)
        self.assertEqual([mapping_db.mapping_id], mappings)
        groups = self._db_api.list_groups()
        self.assertEqual([], groups)
        new_mapping_db = self._db_api.get_mapping(mapping_db.mapping_id)
        self.assertEqual(None, new_mapping_db.group_id)

    def test_list_mappings_from_group(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        group_db = self._db_api.create_group('test_group')
        mapping_tiny = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        mapping_small = self._db_api.create_mapping(
            value='m1.small',
            cost='3.1337',
            map_type='flat',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        self._db_api.create_mapping(
            value='m1.large',
            cost='42',
            map_type='flat',
            field_id=field_db.field_id)
        mappings = self._db_api.list_mappings(field_uuid=field_db.field_id,
                                              group_uuid=group_db.group_id)
        self.assertEqual([mapping_tiny.mapping_id,
                          mapping_small.mapping_id],
                         mappings)

    def test_list_mappings_without_group(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        group_db = self._db_api.create_group('test_group')
        self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        self._db_api.create_mapping(
            value='m1.small',
            cost='3.1337',
            map_type='flat',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        mapping_no_group = self._db_api.create_mapping(
            value='m1.large',
            cost='42',
            map_type='flat',
            field_id=field_db.field_id)
        mappings = self._db_api.list_mappings(field_uuid=field_db.field_id,
                                              no_group=True)
        self.assertEqual([mapping_no_group.mapping_id],
                         mappings)

    # Service tests
    @mock.patch.object(uuidutils, 'generate_uuid',
                       return_value=FAKE_UUID)
    def test_create_service(self, patch_generate_uuid):
        self._db_api.create_service('compute')
        services = self._db_api.list_services()
        self.assertEqual([FAKE_UUID], services)
        patch_generate_uuid.assert_called_once()

    def test_create_duplicate_service(self):
        self._db_api.create_service('compute')
        self.assertRaises(api.ServiceAlreadyExists,
                          self._db_api.create_service,
                          'compute')

    def test_delete_service_by_name(self):
        self._db_api.create_service('compute')
        self._db_api.delete_service('compute')
        services = self._db_api.list_services()
        self.assertEqual([], services)

    def test_delete_service_by_uuid(self):
        service_db = self._db_api.create_service('compute')
        self._db_api.delete_service(uuid=service_db.service_id)
        services = self._db_api.list_services()
        self.assertEqual([], services)

    def test_delete_unknown_service_by_name(self):
        self.assertRaises(api.NoSuchService,
                          self._db_api.delete_service,
                          'dummy')

    def test_delete_unknown_service_by_uuid(self):
        self.assertRaises(
            api.NoSuchService,
            self._db_api.delete_service,
            uuid='6e8de9fc-ee17-4b60-b81a-c9320e994e76')

    # Field tests
    def test_create_field_in_existing_service(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        fields = self._db_api.list_fields(service_db.service_id)
        self.assertEqual([field_db.field_id], fields)

    def test_create_duplicate_field(self):
        service_db = self._db_api.create_service('compute')
        self._db_api.create_field(service_db.service_id,
                                  'flavor')
        self.assertRaises(api.FieldAlreadyExists,
                          self._db_api.create_field,
                          service_db.service_id,
                          'flavor')

    def test_delete_field(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id, 'flavor')
        self._db_api.delete_field(field_db.field_id)
        services = self._db_api.list_services()
        self.assertEqual([service_db.service_id], services)
        fields = self._db_api.list_fields(service_db.service_id)
        self.assertEqual([], fields)

    def test_delete_unknown_field(self):
        self.assertRaises(api.NoSuchField,
                          self._db_api.delete_field,
                          uuidutils.generate_uuid())

    def test_recursive_delete_field_from_service(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        self._db_api.delete_service(uuid=service_db.service_id)
        self.assertRaises(api.NoSuchField,
                          self._db_api.get_field,
                          field_db.field_id)

    # Mapping tests
    def test_create_mapping(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        mapping_db = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        mappings = self._db_api.list_mappings(field_uuid=field_db.field_id)
        self.assertEqual([mapping_db.mapping_id], mappings)

    def test_list_mappings_from_services(self):
        service_db = self._db_api.create_service('compute')
        mapping_db = self._db_api.create_mapping(
            cost='1.337',
            map_type='flat',
            service_id=service_db.service_id)
        mappings = self._db_api.list_mappings(
            service_uuid=service_db.service_id)
        self.assertEqual([mapping_db.mapping_id], mappings)

    def test_list_mappings_from_fields(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        mapping_db = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        mappings = self._db_api.list_mappings(
            field_uuid=field_db.field_id)
        self.assertEqual([mapping_db.mapping_id], mappings)

    def test_create_mapping_with_incorrect_type(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        self.assertRaises(api.NoSuchType,
                          self._db_api.create_mapping,
                          value='m1.tiny',
                          cost='1.337',
                          map_type='invalid',
                          field_id=field_db.field_id)

    def test_create_mapping_with_two_parents(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        self.assertRaises(ValueError,
                          self._db_api.create_mapping,
                          value='m1.tiny',
                          cost='1.337',
                          map_type='flat',
                          service_id=service_db.service_id,
                          field_id=field_db.field_id)

    def test_update_mapping(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        mapping_db = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        new_mapping_db = self._db_api.update_mapping(
            uuid=mapping_db.mapping_id,
            value='42',
            map_type='rate')
        self.assertEqual('42', new_mapping_db.value)
        self.assertEqual('rate', new_mapping_db.map_type)

    def test_update_mapping_inside_group(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        mapping_db = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        group_db = self._db_api.create_group('test_group')
        new_mapping_db = self._db_api.update_mapping(
            mapping_db.mapping_id,
            value='42',
            map_type='rate',
            group_id=group_db.group_id)
        self.assertEqual('42', new_mapping_db.value)
        self.assertEqual('rate', new_mapping_db.map_type)
        self.assertEqual(group_db.id, new_mapping_db.group_id)

    def test_delete_mapping(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        mapping_db = self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        self._db_api.delete_mapping(mapping_db.mapping_id)
        mappings = self._db_api.list_mappings(field_uuid=field_db.field_id)
        self.assertEqual([], mappings)

    # Processing tests
    def test_load_billing_rates(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        group_db = self._db_api.create_group('test_group')
        self._db_api.create_mapping(
            cost='1.42',
            map_type='rate',
            service_id=service_db.service_id)
        self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        self._db_api.create_mapping(
            value='m1.large',
            cost='13.37',
            map_type='rate',
            field_id=field_db.field_id,
            group_id=group_db.group_id)
        self._hash.reload_config()
        service_expect = {
            'compute': {
                '_DEFAULT_': {
                    'cost': decimal.Decimal('1.42'),
                    'type': 'rate'}}}

        field_expect = {
            'compute': {
                'flavor': {
                    '_DEFAULT_': {
                        'm1.tiny': {
                            'cost': decimal.Decimal('1.337'),
                            'type': 'flat'}},
                    'test_group': {
                        'm1.large': {
                            'cost': decimal.Decimal('13.37'),
                            'type': 'rate'}}}}}
        self.assertEqual(service_expect,
                         self._hash._service_mappings)
        self.assertEqual(field_expect,
                         self._hash._field_mappings)

    def test_process_service_map(self):
        service_db = self._db_api.create_service('compute')
        group_db = self._db_api.create_group('test_group')
        self._db_api.create_mapping(
            cost='1.337',
            map_type='flat',
            service_id=service_db.service_id,
            group_id=group_db.group_id)
        self._db_api.create_mapping(
            cost='1.42',
            map_type='flat',
            service_id=service_db.service_id)
        self._hash.reload_config()
        actual_data = CK_RESOURCES_DATA[:]
        expected_data = CK_RESOURCES_DATA[:]
        compute_list = expected_data[0]['usage']['compute']
        compute_list[0]['billing'] = {'price': decimal.Decimal('2.757')}
        compute_list[1]['billing'] = {'price': decimal.Decimal('2.757')}
        compute_list[2]['billing'] = {'price': decimal.Decimal('2.757')}
        self._hash.process(actual_data)
        self.assertEqual(expected_data, actual_data)

    def test_process_field_map(self):
        service_db = self._db_api.create_service('compute')
        flavor_field = self._db_api.create_field(service_db.service_id,
                                                 'flavor')
        image_field = self._db_api.create_field(service_db.service_id,
                                                'image_id')
        group_db = self._db_api.create_group('test_group')
        self._db_api.create_mapping(
            value='m1.nano',
            cost='1.337',
            map_type='flat',
            field_id=flavor_field.field_id,
            group_id=group_db.group_id)
        self._db_api.create_mapping(
            value='a41fba37-2429-4f15-aa00-b5bc4bf557bf',
            cost='1.10',
            map_type='rate',
            field_id=image_field.field_id,
            group_id=group_db.group_id)
        self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.42',
            map_type='flat',
            field_id=flavor_field.field_id)
        self._hash.reload_config()
        actual_data = CK_RESOURCES_DATA[:]
        expected_data = CK_RESOURCES_DATA[:]
        compute_list = expected_data[0]['usage']['compute']
        compute_list[0]['billing'] = {'price': decimal.Decimal('1.337')}
        compute_list[1]['billing'] = {'price': decimal.Decimal('1.42')}
        compute_list[2]['billing'] = {'price': decimal.Decimal('1.47070')}
        self._hash.process(actual_data)
        self.assertEqual(expected_data, actual_data)

    def test_process_billing(self):
        service_db = self._db_api.create_service('compute')
        field_db = self._db_api.create_field(service_db.service_id,
                                             'flavor')
        self._db_api.create_group('test_group')
        self._db_api.create_mapping(
            cost='1.00',
            map_type='flat',
            service_id=service_db.service_id)
        self._db_api.create_mapping(
            value='m1.nano',
            cost='1.337',
            map_type='flat',
            field_id=field_db.field_id)
        self._db_api.create_mapping(
            value='m1.tiny',
            cost='1.42',
            map_type='flat',
            field_id=field_db.field_id)
        self._hash.reload_config()
        actual_data = CK_RESOURCES_DATA[:]
        expected_data = CK_RESOURCES_DATA[:]
        compute_list = expected_data[0]['usage']['compute']
        compute_list[0]['billing'] = {'price': decimal.Decimal('1.337')}
        compute_list[1]['billing'] = {'price': decimal.Decimal('1.42')}
        compute_list[2]['billing'] = {'price': decimal.Decimal('1.42')}
        self._hash.process(actual_data)
        self.assertEqual(expected_data, actual_data)
