# -*- coding: utf-8 -*-
# Copyright 2016 Objectif Libre
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
import testtools

from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty.tests import transformers as t_transformers
from cloudkitty.tests.utils import is_functional_test

TRANS_METADATA = {
    'availability_zone': 'nova',
    'flavor': 'm1.nano',
    'image_id': 'f5600101-8fa2-4864-899e-ebcb7ed6b568',
    'memory': '64',
    'name': 'prod1',
    'vcpus': '1'}


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class TransformerBaseTest(tests.TestCase):
    def test_strip_resource_on_dict(self):
        metadata = copy.deepcopy(samples.COMPUTE_METADATA)
        t_test = t_transformers.Transformer()
        result = t_test.strip_resource_data('compute', metadata)
        self.assertEqual(TRANS_METADATA, result)

    def test_strip_resource_with_no_rules(self):
        metadata = copy.deepcopy(samples.COMPUTE_METADATA)
        t_test = t_transformers.Transformer()
        result = t_test.strip_resource_data('unknown', metadata)
        self.assertEqual(samples.COMPUTE_METADATA, result)

    def test_strip_resource_with_func(self):
        metadata = {'test': 'dummy'}
        t_test = t_transformers.Transformer()
        result = t_test.strip_resource_data('test', metadata)
        self.assertEqual({'test': 'ok'}, result)

    def test_strip_resource_with_stripping_function(self):
        metadata = {}
        t_test = t_transformers.Transformer()
        result = t_test.strip_resource_data('network', metadata)
        self.assertEqual({'test': 'ok'}, result)

    def test_strip_resource_with_subitem(self):
        test_obj = t_transformers.EmptyClass()
        test_obj.metadata = copy.deepcopy(samples.COMPUTE_METADATA)
        t_test = t_transformers.TransformerMeta()
        result = t_test.strip_resource_data('compute', test_obj)
        self.assertEqual(TRANS_METADATA, result)

    def test_strip_resource_with_attributes(self):
        test_obj = t_transformers.EmptyClass()
        test_obj.metadata = t_transformers.ClassWithAttr()
        t_test = t_transformers.TransformerMeta()
        result = t_test.strip_resource_data('compute', test_obj)
        self.assertEqual(TRANS_METADATA, result)
