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
"""Test cloudkitty/api/v1/types."""

import testtools

from oslotest import base
from wsme import types as wtypes

from cloudkitty.api.v1 import types
from cloudkitty.tests.utils import is_functional_test


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class TestTypes(base.BaseTestCase):

    def setUp(self):
        super(TestTypes, self).setUp()
        self.uuidtype = types.UuidType
        self.multitype = types.MultiType(wtypes.text, int, float, dict)

    def test_valid_uuid_values(self):
        valid_values = ['7977999e-2e25-11e6-a8b2-df30b233ffcb',
                        'ac55b000-a05b-4832-b2ff-265a034886ab',
                        '39dbd39d-f663-4444-a795-fb19d81af136']
        for valid_value in valid_values:
            self.uuidtype.validate(valid_value)

    def test_invalid_uuid_values(self):
        invalid_values = ['dxwegycw', '1234567', '#@%^&$*!']
        for invalid_value in invalid_values:
            self.assertRaises(ValueError, self.uuidtype.validate,
                              invalid_value)

    def test_valid_multi_values(self):
        valid_values = ['string_value', 123, 23.4, {'key': 'value'}]
        for valid_value in valid_values:
            self.multitype.validate(valid_value)

    def test_invalid_multi_values(self):
        invalid_values = [[1, 2, 3], ('a', 'b', 'c')]
        for invalid_value in invalid_values:
            self.assertRaises(ValueError, self.multitype.validate,
                              invalid_value)
