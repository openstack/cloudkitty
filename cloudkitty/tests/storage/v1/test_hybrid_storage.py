# -*- coding: utf-8 -*-
# Copyright 2017 Objectif Libre
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
# @author: Luka Peschke
#
import mock
import testtools

from gnocchiclient import exceptions as gexc

from cloudkitty import storage
from cloudkitty import tests
from cloudkitty.tests import test_utils
from cloudkitty.tests.utils import is_functional_test


class BaseHybridStorageTest(tests.TestCase):

    @mock.patch('cloudkitty.utils.load_conf', new=test_utils.load_conf)
    def setUp(self):
        super(BaseHybridStorageTest, self).setUp()
        self.conf.set_override('backend', 'hybrid', 'storage')
        self.conf.set_override('version', '1', 'storage')
        self.storage = storage.get_storage(conf=test_utils.load_conf())
        with mock.patch.object(
                self.storage.storage._hybrid_backend, 'init'):
            self.storage.init()


class PermissiveDict(object):
    """Allows to check a single key of a dict in an assertion.

    Example:
    >>> mydict = {'a': 'A', 'b': 'B'}
    >>> checker = PermissiveDict('A', key='a')
    >>> checker == mydict
    True
    """
    def __init__(self, value, key='name'):
        self.key = key
        self.value = value

    def __eq__(self, other):
        return self.value == other.get(self.key)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class HybridStorageTestGnocchi(BaseHybridStorageTest):

    def setUp(self):
        super(HybridStorageTestGnocchi, self).setUp()

    def tearDown(self):
        super(HybridStorageTestGnocchi, self).tearDown()

    def _init_storage(self, archive_policy=False, res_type=False):
        with mock.patch.object(self.storage.storage._hybrid_backend._conn,
                               'archive_policy',
                               spec=['get', 'create']) as pol_mock:
            if not archive_policy:
                pol_mock.get.side_effect = gexc.ArchivePolicyNotFound
            else:
                pol_mock.create.side_effect = gexc.ArchivePolicyAlreadyExists
            with mock.patch.object(self.storage.storage._hybrid_backend._conn,
                                   'resource_type',
                                   spec=['get', 'create']) as rtype_mock:
                if not res_type:
                    rtype_mock.get.side_effect = gexc.ResourceTypeNotFound
                else:
                    rtype_mock.create.side_effect \
                        = gexc.ResourceTypeAlreadyExists

                self.storage.init()
                rtype_data = (self.storage.storage
                              ._hybrid_backend._resource_type_data)
                rtype_calls = list()
                for val in rtype_data.values():
                    rtype_calls.append(
                        mock.call(PermissiveDict(val['name'], key='name')))
                if res_type:
                    rtype_mock.create.assert_not_called()
                else:
                    rtype_mock.create.assert_has_calls(
                        rtype_calls, any_order=True)
            pol_mock.get.assert_called_once_with(
                self.storage.storage._hybrid_backend._archive_policy_name)
            if archive_policy:
                pol_mock.create.assert_not_called()
            else:
                apolicy = {
                    'name': (self.storage.storage
                             ._hybrid_backend._archive_policy_name),
                    'back_window': 0,
                    'aggregation_methods':
                        ['std', 'count', 'min', 'max', 'sum', 'mean'],
                }
                apolicy['definition'] = (self.storage.storage
                                         ._hybrid_backend
                                         ._archive_policy_definition)
                pol_mock.create.assert_called_once_with(apolicy)

    def test_init_no_res_type_no_policy(self):
        self._init_storage()

    def test_init_with_res_type_no_policy(self):
        self._init_storage(res_type=True)

    def test_init_no_res_type_with_policy(self):
        self._init_storage(archive_policy=True)

    def test_init_with_res_type_with_policy(self):
        self._init_storage(res_type=True, archive_policy=True)
