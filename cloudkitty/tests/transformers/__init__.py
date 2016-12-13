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
from cloudkitty.tests import samples
from cloudkitty import transformer


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
    def __init__(self, items=samples.COMPUTE_METADATA):
        for key, val in items.items():
            setattr(self, key, val)
