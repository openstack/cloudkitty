# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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
import abc

import six
from stevedore import extension

TRANSFORMERS_NAMESPACE = 'cloudkitty.transformers'


def get_transformers():
    transformers = {}
    transformer_exts = extension.ExtensionManager(
        TRANSFORMERS_NAMESPACE,
        invoke_on_load=True)
    for transformer in transformer_exts:
        t_name = transformer.name
        t_obj = transformer.obj
        transformers[t_name] = t_obj
    return transformers


@six.add_metaclass(abc.ABCMeta)
class BaseTransformer(object):
    metadata_item = ''

    def generic_strip(self, datatype, data):
        metadata = getattr(data, self.metadata_item, data)
        mappings = getattr(self, datatype + '_map', {})
        result = {}
        for key, transform in mappings.items():
            if isinstance(transform, list):
                for meta_key in transform:
                    if key not in result or result[key] is None:
                        try:
                            data = getattr(metadata, meta_key)
                        except AttributeError:
                            data = metadata.get(meta_key)
                        result[key] = data
            else:
                trans_data = transform(self, metadata)
                if trans_data:
                    result[key] = trans_data
        return result

    def strip_resource_data(self, res_type, res_data):
        res_type = res_type.replace('.', '_')
        strip_func = getattr(self, '_strip_' + res_type, None)
        if strip_func:
            return strip_func(res_data)
        return self.generic_strip(res_type, res_data) or res_data

    def get_metadata(self, res_type):
        """Return list of metadata available for given resource type."""

        return []
