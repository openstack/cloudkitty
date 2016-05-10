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

import six

from cloudkitty import tests
from cloudkitty.tests import samples
from cloudkitty import transformer

TRANS_METADATA = {
    'availability_zone': 'nova',
    'flavor': 'm1.nano',
    'image_id': 'f5600101-8fa2-4864-899e-ebcb7ed6b568',
    'memory': '64',
    'name': 'prod1',
    'vcpus': '1'}


class Transformer(transformer.BaseTransformer):
    compute_map = {
        'name': ['name', 'display_name'],
        'flavor': ['flavor', 'flavor.name', 'instance_type'],
        'vcpus': ['vcpus'],
        'memory': ['memory', 'memory_mb'],
        'image_id': ['image_id', 'image.id', 'image_meta.base_image_ref'],
        'availability_zone': [
            'availability_zone',
            'OS-EXT-AZ.availability_zone'],
    }
    volume_map = {
        'volume_id': ['volume_id'],
        'name': ['display_name'],
        'availability_zone': ['availability_zone'],
        'size': ['size'],
    }
    test_map = {'test': lambda x, y: 'ok'}

    def _strip_network(self, res_metadata):
        return {'test': 'ok'}


class TransformerMeta(Transformer):
    metadata_item = 'metadata'


class EmptyClass(object):
    pass


class ClassWithAttr(object):
    def __init__(self):
        for key, val in six.iteritems(samples.COMPUTE_METADATA):
            setattr(self, key, val)


class TransformerBaseTest(tests.TestCase):
    def setUp(self):
        super(TransformerBaseTest, self).setUp()

    def test_strip_resource_on_dict(self):
        metadata = copy.deepcopy(samples.COMPUTE_METADATA)
        t_test = Transformer()
        result = t_test.strip_resource_data('compute', metadata)
        self.assertEqual(TRANS_METADATA, result)

    def test_strip_resource_with_no_rules(self):
        metadata = copy.deepcopy(samples.COMPUTE_METADATA)
        t_test = Transformer()
        result = t_test.strip_resource_data('unknown', metadata)
        self.assertEqual(samples.COMPUTE_METADATA, result)

    def test_strip_resource_with_func(self):
        metadata = {'test': 'dummy'}
        t_test = Transformer()
        result = t_test.strip_resource_data('test', metadata)
        self.assertEqual({'test': 'ok'}, result)

    def test_strip_resource_with_stripping_function(self):
        metadata = {}
        t_test = Transformer()
        result = t_test.strip_resource_data('network', metadata)
        self.assertEqual({'test': 'ok'}, result)

    def test_strip_resource_with_subitem(self):
        test_obj = EmptyClass()
        test_obj.metadata = copy.deepcopy(samples.COMPUTE_METADATA)
        t_test = TransformerMeta()
        result = t_test.strip_resource_data('compute', test_obj)
        self.assertEqual(TRANS_METADATA, result)

    def test_strip_resource_with_attributes(self):
        test_obj = EmptyClass()
        test_obj.metadata = ClassWithAttr()
        t_test = TransformerMeta()
        result = t_test.strip_resource_data('compute', test_obj)
        self.assertEqual(TRANS_METADATA, result)
