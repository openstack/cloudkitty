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
from cloudkitty.tests.utils import is_functional_test
from cloudkitty.transformer import gnocchi


GNOCCHI_COMPUTE = {
    'id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'display_name': 'test',
    'flavor_id': '6aa7b1ce-317c-11e6-92d2-835668472674',
    'image_ref': 'http://fakeglance/c8ae2e38-316d-11e6-b19a-dbee663ddaee',
    'metrics': {}}

TRANS_COMPUTE = {
    'instance_id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'resource_id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'name': 'test',
    'flavor_id': '6aa7b1ce-317c-11e6-92d2-835668472674',
    'image_id': 'c8ae2e38-316d-11e6-b19a-dbee663ddaee',
    'metrics': {}}

GNOCCHI_IMAGE = {
    'id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'container_format': 'bare',
    'disk_format': 'raw',
    'metrics': {}}

TRANS_IMAGE = {
    'resource_id': '2f58a438-3169-11e6-b36c-bfe1fa3241fe',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'container_format': 'bare',
    'disk_format': 'raw',
    'metrics': {}}

GNOCCHI_VOLUME = {
    'id': '17992d58-316f-11e6-9528-1379eed8ebe4',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'display_name': 'vol1',
    'volume_type': 'lvmdriver-1',
    'metrics': {}}

TRANS_VOLUME = {
    'resource_id': '17992d58-316f-11e6-9528-1379eed8ebe4',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'name': 'vol1',
    'volume_type': 'lvmdriver-1',
    'metrics': {}}

GNOCCHI_NETWORK = {
    'id': '02f8e84e-317d-11e6-ad23-af0423cd2a97',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'name': 'network1',
    'metrics': {}}

TRANS_NETWORK = {
    'resource_id': '02f8e84e-317d-11e6-ad23-af0423cd2a97',
    'project_id': '4480c638-3169-11e6-91de-a3bd3a7d3afb',
    'user_id': '576808d8-3169-11e6-992b-5f931fc671df',
    'name': 'network1',
    'metrics': {}}


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class GnocchiTransformerTest(tests.TestCase):
    def test_strip_gnocchi_compute(self):
        resource = copy.deepcopy(GNOCCHI_COMPUTE)
        t_test = gnocchi.GnocchiTransformer()
        result = t_test.strip_resource_data('compute', resource)
        self.assertEqual(TRANS_COMPUTE, result)

    def test_strip_gnocchi_image(self):
        resource = copy.deepcopy(GNOCCHI_IMAGE)
        t_test = gnocchi.GnocchiTransformer()
        result = t_test.strip_resource_data('image', resource)
        self.assertEqual(TRANS_IMAGE, result)

    def test_strip_gnocchi_volume(self):
        resource = copy.deepcopy(GNOCCHI_VOLUME)
        t_test = gnocchi.GnocchiTransformer()
        result = t_test.strip_resource_data('volume', resource)
        self.assertEqual(TRANS_VOLUME, result)

    def test_strip_gnocchi_network(self):
        resource = copy.deepcopy(GNOCCHI_NETWORK)
        t_test = gnocchi.GnocchiTransformer()
        result = t_test.strip_resource_data('network', resource)
        self.assertEqual(TRANS_NETWORK, result)
