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

from cloudkitty import tests
from cloudkitty.tests import transformers as t_transformers
from cloudkitty.transformer import ceilometer

CEIL_COMPUTE = {
    'availability_zone': 'nova',
    'display_name': 'test',
    'instance_type': 'm1.nano',
    'image.id': 'c8ae2e38-316d-11e6-b19a-dbee663ddaee',
    'memory_mb': 64,
    'user_metadata.meta1': 'test1',
    'vcpus': '1'}

TRANS_COMPUTE = {
    'instance_id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'availability_zone': 'nova',
    'metadata': {
        'meta1': 'test1'},
    'name': 'test',
    'flavor': 'm1.nano',
    'image_id': 'c8ae2e38-316d-11e6-b19a-dbee663ddaee',
    'memory': 64,
    'vcpus': '1'}

CEIL_VOLUME = {
    'availability_zone': 'az1',
    'volume_id': '17992d58-316f-11e6-9528-1379eed8ebe4',
    'display_name': 'vol1',
    'size': 10}

TRANS_VOLUME = {
    'volume_id': '17992d58-316f-11e6-9528-1379eed8ebe4',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'availability_zone': 'az1',
    'name': 'vol1',
    'size': 10}

CEIL_IMAGE = {
    'status': 'active',
    'name': 'Cirros',
    'deleted': 'False',
    'disk_format': 'ami',
    'id': 'c4a0d12e-88ff-43e1-b182-f95dfe75e40c',
    'protected': 'False',
    'container_format': 'ami',
    'is_public': 'False',
    'size': '25165824'
}

TRANS_IMAGE = {
    'image_id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'container_format': 'ami',
    'deleted': 'False',
    'disk_format': 'ami',
    'is_public': 'False',
    'name': 'Cirros',
    'protected': 'False',
    'size': '25165824',
    'status': 'active'
}


class CeilometerTransformerTest(tests.TestCase):
    def setUp(self):
        super(CeilometerTransformerTest, self).setUp()

    def generate_ceilometer_resource(self, data):
        resource = t_transformers.ClassWithAttr({
            'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
            'resource_id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
            'user_id': '576808d8-3169-11e6-992b-5f931fc671df'})
        resource.metadata = copy.deepcopy(data)
        return resource

    def test_strip_ceilometer_compute(self):
        resource = self.generate_ceilometer_resource(CEIL_COMPUTE)
        t_test = ceilometer.CeilometerTransformer()
        result = t_test.strip_resource_data('compute', resource)
        self.assertEqual(TRANS_COMPUTE, result)

    def test_strip_ceilometer_volume(self):
        resource = self.generate_ceilometer_resource(CEIL_VOLUME)
        t_test = ceilometer.CeilometerTransformer()
        result = t_test.strip_resource_data('volume', resource)
        self.assertEqual(TRANS_VOLUME, result)

    def test_strip_ceilometer_image(self):
        resource = self.generate_ceilometer_resource(CEIL_IMAGE)
        t_test = ceilometer.CeilometerTransformer()
        result = t_test.strip_resource_data('image', resource)
        self.assertEqual(TRANS_IMAGE, result)
