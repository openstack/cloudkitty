# -*- coding: utf-8 -*-
# Copyright 2018 Objectif Libre
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
# @author: Martin CAMEY
#
DEFAULT_METRICS_CONF = {
    'name': 'OpenStack',

    'fetcher': 'keystone',
    'collector': 'gnocchi',

    'period': 3600,
    'wait_periods': 2,
    'window': 1800,

    'services_objects': {
        'compute': 'instance',
        'volume': 'volume',
        'network.bw.out': 'instance_network_interface',
        'network.bw.in': 'instance_network_interface',
        'network.floating': 'network',
        'image': 'image',
        'radosgw.usage': 'ceph_account',
    },

    'metrics': {
        'vcpus': {
            'resource': 'instance',
            'unit': 'instance',
            'factor': 1,
            'aggregation_method': 'max',
            'countable_unit': True,
        },
        'memory': {
            'resource': 'instance',
            'unit': 'instance',
            'factor': 1,
            'aggregation_method': 'max',
            'countable_unit': True,
        },
        'cpu': {
            'resource': 'instance',
            'unit': 'instance',
            'factor': 1,
            'aggregation_method': 'max',
            'countable_unit': True,
        },
        'disk.root.size': {
            'resource': 'instance',
            'unit': 'instance',
            'factor': 1,
            'aggregation_method': 'max',
            'countable_unit': True,
        },
        'disk.ephemeral.size': {
            'resource': 'instance',
            'unit': 'instance',
            'factor': 1,
            'aggregation_method': 'max',
            'countable_unit': True,
        },
        'image.size': {
            'resource': 'image',
            'unit': 'MiB',
            'factor': 1 / 1048576,
            'aggregation_method': 'max',
        },
        'image.download': {
            'resource': 'image',
            'unit': 'MiB',
            'factor': 1 / 1048576,
            'aggregation_method': 'max',
        },
        'image.serve': {
            'resource': 'image',
            'unit': 'MiB',
            'factor': 1 / 1048576,
            'aggregation_method': 'max',
        },
        'volume.size': {
            'resource': 'volume',
            'unit': 'GiB',
            'factor': 1,
            'aggregation_method': 'max',
        },
        'network.outgoing.bytes': {
            'resource': 'instance_network_interface',
            'unit': 'MB',
            'factor': 1 / 1000000,
            'aggregation_method': 'max',
        },
        'network.incoming.bytes': {
            'resource': 'instance_network_interface',
            'unit': 'MB',
            'factor': 1 / 1000000,
            'aggregation_method': 'max',
        },
        'ip.floating': {
            'resource': 'network',
            'unit': 'ip',
            'factor': 1,
            'aggregation_method': 'max',
            'countable_unit': True,
        },
        'radosgw.objects.size': {
            'resource': 'ceph_account',
            'unit': 'GiB',
            'factor': 1 / 1073741824,
            'aggregation_method': 'max',
        },
    },
}
