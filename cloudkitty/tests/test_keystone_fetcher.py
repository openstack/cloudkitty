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
import testtools
import unittest

import mock
from oslo_utils import uuidutils

from cloudkitty.fetcher import keystone
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test


class FakeRole(object):
    def __init__(self, name, uuid=None):
        self.id = uuid if uuid else uuidutils.generate_uuid()
        self.name = name


class FakeTenant(object):
    def __init__(self, id):
        self.id = id


class FakeKeystoneClient(object):

    user_id = 'd89e3fee-2b92-4387-b564-63901d62e591'

    def __init__(self, **kwargs):
        pass

    class FakeTenants(object):
        @classmethod
        def list(cls):
            return [FakeTenant('f266f30b11f246b589fd266f85eeec39'),
                    FakeTenant('4dfb25b0947c4f5481daf7b948c14187')]

    class FakeRoles(object):
        roles_mapping = {
            'd89e3fee-2b92-4387-b564-63901d62e591': {
                'f266f30b11f246b589fd266f85eeec39': [FakeRole('rating'),
                                                     FakeRole('admin')],
                '4dfb25b0947c4f5481daf7b948c14187': [FakeRole('admin')]}}

        @classmethod
        def roles_for_user(cls, user_id, tenant, **kwargs):
            return cls.roles_mapping[user_id][tenant.id]

    roles = FakeRoles()
    tenants = FakeTenants()


def Client(**kwargs):
    return FakeKeystoneClient(**kwargs)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class KeystoneFetcherTest(tests.TestCase):
    def setUp(self):
        super(KeystoneFetcherTest, self).setUp()
        self.conf.set_override('backend', 'keystone', 'tenant_fetcher')
        self.conf.import_group('keystone_fetcher',
                               'cloudkitty.fetcher.keystone')

    @unittest.SkipTest
    def test_keystone_fetcher_filter_list(self):
        kclient = 'keystoneclient.client.Client'
        with mock.patch(kclient) as kclientmock:
            kclientmock.return_value = Client()
            fetcher = keystone.KeystoneFetcher()
            kclientmock.assert_called_once_with(
                auth_url='http://127.0.0.1:5000/v2.0',
                username='cloudkitty',
                password='cloudkitty',
                tenant_name='cloudkitty',
                region_name='RegionOne')
            tenants = fetcher.get_tenants()
            self.assertEqual(['f266f30b11f246b589fd266f85eeec39'], tenants)
