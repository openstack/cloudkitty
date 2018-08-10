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
"""Test SummaryModel objects."""
import testtools

from oslotest import base

from cloudkitty.api.v1.datamodels import report
from cloudkitty.tests.utils import is_functional_test


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class TestSummary(base.BaseTestCase):

    def setUp(self):
        super(TestSummary, self).setUp()

    def test_nulls(self):
        s = report.SummaryModel(begin=None,
                                end=None,
                                tenant_id=None,
                                res_type=None,
                                rate=None)
        self.assertIsNone(s.begin)
        self.assertIsNone(s.end)
        self.assertEqual(s.tenant_id, "ALL")
        self.assertEqual(s.res_type, "ALL")
        self.assertEqual(s.rate, "0")
