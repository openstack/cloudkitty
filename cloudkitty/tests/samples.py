# -*- coding: utf-8 -*-
# Copyright 2015 Objectif Libre
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
import decimal

from cloudkitty import utils as ck_utils

TENANT = 'f266f30b11f246b589fd266f85eeec39'
INITIAL_TIMESTAMP = 1420070400
FIRST_PERIOD_BEGIN = INITIAL_TIMESTAMP
FIRST_PERIOD_BEGIN_ISO = ck_utils.ts2iso(FIRST_PERIOD_BEGIN)
FIRST_PERIOD_END = FIRST_PERIOD_BEGIN + 3600
FIRST_PERIOD_END_ISO = ck_utils.ts2iso(FIRST_PERIOD_END)
SECOND_PERIOD_BEGIN = FIRST_PERIOD_END
SECOND_PERIOD_BEGIN_ISO = ck_utils.ts2iso(SECOND_PERIOD_BEGIN)
SECOND_PERIOD_END = SECOND_PERIOD_BEGIN + 3600
SECOND_PERIOD_END_ISO = ck_utils.ts2iso(SECOND_PERIOD_END)

COMPUTE_METADATA = {
    'availability_zone': 'nova',
    'flavor': 'm1.nano',
    'image_id': 'f5600101-8fa2-4864-899e-ebcb7ed6b568',
    'instance_id': '26c084e1-b8f1-4cbc-a7ec-e8b356788a17',
    'resource_id': '1558f911-b55a-4fd2-9173-c8f1f23e5639',
    'memory': '64',
    'metadata': {
        'farm': 'prod'
    },
    'name': 'prod1',
    'project_id': 'f266f30b11f246b589fd266f85eeec39',
    'user_id': '55b3379b949243009ee96972fbf51ed1',
    'vcpus': '1'}

IMAGE_METADATA = {
    'checksum': '836c69cbcd1dc4f225daedbab6edc7c7',
    'resource_id': '7b5b73f2-9181-4307-a710-b1aa6472526d',
    'container_format': 'aki',
    'created_at': '2014-06-04T16:26:01',
    'deleted': 'False',
    'deleted_at': 'None',
    'disk_format': 'aki',
    'is_public': 'True',
    'min_disk': '0',
    'min_ram': '0',
    'name': 'cirros-0.3.2-x86_64-uec-kernel',
    'protected': 'False',
    'size': '4969360',
    'status': 'active',
    'updated_at': '2014-06-04T16:26:02'}

FIRST_PERIOD = {
    'begin': FIRST_PERIOD_BEGIN,
    'end': FIRST_PERIOD_END}

SECOND_PERIOD = {
    'begin': SECOND_PERIOD_BEGIN,
    'end': SECOND_PERIOD_END}

COLLECTED_DATA = [{
    'period': FIRST_PERIOD,
    'usage': {
        'compute': [{
            'desc': COMPUTE_METADATA,
            'vol': {
                'qty': decimal.Decimal(1.0),
                'unit': 'instance'}}],
        'image': [{
            'desc': IMAGE_METADATA,
            'vol': {
                'qty': decimal.Decimal(1.0),
                'unit': 'image'}}]
    }}, {
    'period': SECOND_PERIOD,
    'usage': {
        'compute': [{
            'desc': COMPUTE_METADATA,
            'vol': {
                'qty': decimal.Decimal(1.0),
                'unit': 'instance'}}]
    }}]

RATED_DATA = copy.deepcopy(COLLECTED_DATA)
RATED_DATA[0]['usage']['compute'][0]['rating'] = {
    'price': decimal.Decimal('0.42')}
RATED_DATA[0]['usage']['image'][0]['rating'] = {
    'price': decimal.Decimal('0.1337')}
RATED_DATA[1]['usage']['compute'][0]['rating'] = {
    'price': decimal.Decimal('0.42')}


def split_storage_data(raw_data):
    final_data = []
    for frame in raw_data:
        frame['period']['begin'] = ck_utils.ts2iso(frame['period']['begin'])
        frame['period']['end'] = ck_utils.ts2iso(frame['period']['end'])
        usage_buffer = frame.pop('usage')
        # Sort to have a consistent result as we are converting it to a list
        for service, data in sorted(usage_buffer.items()):
            new_frame = copy.deepcopy(frame)
            new_frame['usage'] = {service: data}
            new_frame['usage'][service][0]['tenant_id'] = TENANT
            final_data.append(new_frame)
    return final_data


# FIXME(sheeprine): storage is not using decimal for rates, we need to
# transition to decimal.
STORED_DATA = copy.deepcopy(COLLECTED_DATA)
STORED_DATA[0]['usage']['compute'][0]['rating'] = {
    'price': 0.42}
STORED_DATA[0]['usage']['image'][0]['rating'] = {
    'price': 0.1337}
STORED_DATA[1]['usage']['compute'][0]['rating'] = {
    'price': 0.42}

STORED_DATA = split_storage_data(STORED_DATA)

METRICS_CONF = {
    'collector': 'gnocchi',
    'name': 'OpenStack',
    'period': 3600,
    'services': [
        'compute',
        'volume',
        'network.bw.in',
        'network.bw.out',
        'network.floating',
        'image'
    ],
    'services_metrics': {
        'compute': [
            {'vcpus': 'max'},
            {'memory': 'max'},
            {'cpu': 'max'},
            {'disk.root.size': 'max'},
            {'disk.ephemeral.size': 'max'}
        ],
        'image': [
            {'image.size': 'max'},
            {'image.download': 'max'},
            {'image.serve': 'max'}
        ],
        'network.bw.in': [{'network.incoming.bytes': 'max'}],
        'network.bw.out': [{'network.outgoing.bytes': 'max'}],
        'network.floating': [{'ip.floating': 'max'}],
        'volume': [{'volume.size': 'max'}],
        'radosgw.usage': [{'radosgw.objects.size': 'max'}]},
    'services_objects': {
        'compute': 'instance',
        'image': 'image',
        'network.bw.in': 'instance_network_interface',
        'network.bw.out': 'instance_network_interface',
        'network.floating': 'network',
        'volume': 'volume',
        'radosgw.usage': 'ceph_account',
    },
    'metrics_units': {
        'compute': {1: {'unit': 'instance'}},
        'default_unit': {1: {'unit': 'unknown'}},
        'image': {'image.size': {'unit': 'MiB', 'factor': '1/1048576'}},
        'network.bw.in': {'network.incoming.bytes': {
            'unit': 'MB',
            'factor': '1/1000000'}},
        'network.bw.out': {'network.outgoing.bytes': {
            'unit': 'MB',
            'factor': '1/1000000'}},
        'network.floating': {1: {'unit': 'ip'}},
        'volume': {'volume.size': {'unit': 'GiB'}},
        'radosgw.usage': {'radosgw.objects.size': {
            'unit': 'GiB',
            'factor': '1/1073741824'}},
    },
    'wait_periods': 2,
    'window': 1800
}
