#!/usr/bin/env python
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
import calendar
import copy
import csv
import datetime
import json
import random
import sys
import uuid


COMPUTE = {
    "type": "compute",
    "desc": {},
    "vol": {
        "qty": 1,
        "unit": "instance"}}

COMPUTE_RESOURCE = {
    "availability_zone": "nova",
    "flavor": "m1.nano",
    "image_id": "f5600101-8fa2-4864-899e-ebcb7ed6b568",
    "memory": "64",
    "metadata": {
        "farm": "prod"},
    "name": "prod1",
    "project_id": "f266f30b11f246b589fd266f85eeec39",
    "user_id": "55b3379b949243009ee96972fbf51ed1",
    "vcpus": "1"}

IMAGE = {
    "type": "image",
    "desc": {},
    "vol": {
        "qty": 214106112.0,
        "unit": "B"}}

IMAGE_RESOURCE = {
    "name": "cirros-0.3.4-x86_64-uec-ramdisk",
    "checksum": "be575a2b939972276ef675752936977f",
    "disk_format": "ari",
    "protected": "False",
    "container_format": "ari",
    "min_disk": "0",
    "is_public": "True",
    "min_ram": "0",
    "project_id": "f1873b13951542268bf7eed7cf971e52",
    "resource_id": "08017fbc-b13a-4d8d-b002-4eb4eff54cd4",
    "source": "openstack",
    "user_id": "None",
    "size": "214106112"}

VOLUME = {
    "type": "volume",
    "desc": {},
    "vol": {
        "qty": 1,
        "unit": "GB"}}

VOLUME_RESOURCE = {
    'instance_uuid': 'None',
    'status': 'available',
    'display_name': 'test-vol',
    'event_type': 'volume.create.end',
    'availability_zone': 'nova',
    'tenant_id': 'cd27b013b9db4f4099e273e4b9949023',
    'created_at': '2015-04-28 13:34:25',
    'snapshot_id': 'None',
    'volume_type': '314150bc-221f-4676-a7cf-16f12850b217',
    'host': 'volume.devstack@lvmdriver-1#lvmdriver-1',
    'replication_driver_data': 'None',
    'replication_status': 'disabled',
    'volume_id': '2bed6a3d-468a-459b-802b-44930016c0a3',
    'replication_extended_status': 'None',
    'user_id': '2524d5a52ce64a569d131d7dc1dfb455',
    'launched_at': '2015-04-28 13:34:26.869928',
    'size': '1',
    "project_id": "f1873b13951542268bf7eed7cf971e52",
    "resource_id": "08017fbc-b13a-4d8d-b002-4eb4eff54cd4",
    "source": "openstack",
    "user_id": "None"}

NETWORK_BW_IN = {
    "type": "network.bw.in",
    "desc": {},
    "vol": {
        "qty": 4546.0,
        "unit": "B"}}

NETWORK_BW_OUT = {
    "type": "network.bw.out",
    "desc": {},
    "vol": {
        "qty": 50.0,
        "unit": "MB"}}

NETWORK_BW_RESOURCE = {
    'instance_id': 'eef9673d-5d24-43fd-89f5-2929acc7e193',
    'instance_type': '42',
    'mac': 'fa:16:3e:dd:b2:80',
    'fref': 'None',
    'name': 'tap12a7d4e1-fc',
    "project_id": "f1873b13951542268bf7eed7cf971e52",
    "resource_id": "08017fbc-b13a-4d8d-b002-4eb4eff54cd4",
    "source": "openstack",
    "user_id": "None"}

FLOATING = {
    "type": "network.floating",
    "desc": {},
    "vol": {
        "qty": 1.0,
        "unit": "ip"}}

FLOATING_RESOURCE = {
    'router_id': '3d9b2725-fc90-43d0-b119-630e80e1ec51',
    'status': 'DOWN',
    'event_type': 'floatingip.update.end',
    'tenant_id': 'cd27b013b9db4f4099e273e4b9949023',
    'floating_network_id': '14198fb4-dc96-45fb-9dde-546f6b0f892f',
    'host': 'network.devstack',
    'fixed_ip_address': '10.0.0.5',
    'floating_ip_address': '172.24.4.3',
    'port_id': '12a7d4e1-fcc3-4a3c-8e57-c4baf7787b57',
    "project_id": "cd27b013b9db4f4099e273e4b9949023",
    "resource_id": "ebf6485d-7f6f-4c67-97f7-7896324e12d4",
    "source": "openstack",
    "user_id": "7319b5d1269d4166a402868b570aad19",
    'id': 'ebf6485d-7f6f-4c67-97f7-7896324e12d4'}


class VariationMapper(object):
    day_map = {
        0: 'mon',
        1: 'tue',
        2: 'wed',
        3: 'thu',
        4: 'fri',
        5: 'sat',
        6: 'sun'}
    var_map = {
        'mon': {},
        'tue': {},
        'wed': {},
        'thu': {},
        'fri': {},
        'sat': {},
        'sun': {}}

    def __init__(self, default=1.0):
        self.default = default

    def get_var(self, dt):
        weekday = self.day_map[dt.weekday()]
        if weekday in self.var_map:
            wday_map = self.var_map[weekday]
            if dt.hour in wday_map:
                return wday_map[dt.hour]
            elif 'default' in wday_map:
                return wday_map['default']
        elif 'default' in self.var_map:
            return self.var_map['default']
        return self.default


class VolumeVariationMapper(VariationMapper):
    def get_vol(self, dt):
        value = self.get_var(dt)
        var_value = value * 0.1
        return random.gauss(value, var_value)


class BaseGenerator(object):
    base_sample = None
    base_resource = None
    rand = True
    field_maps = {}

    def __init__(self, nb_res=1, var_map=None, vol_map=None):
        self.nb_res = nb_res
        self.var_map = var_map if var_map else VariationMapper()
        self.vol_map = vol_map
        self.init_mapper()
        self.resources = []

    def init_mapper(self):
        pass

    def generate_resources(self):
        for i in range(self.nb_res):
            res = copy.deepcopy(self.base_resource)
            for field, mapping in self.field_maps.items():
                if hasattr(self, mapping):
                    mapping = getattr(self, mapping)
                if isinstance(mapping, dict):
                    if self.rand:
                        value = random.choice(mapping.keys())
                    else:
                        value = mapping.keys()[i]
                    res[field] = value
                    for k, v in mapping[value].items():
                        res[k] = v
                elif isinstance(mapping, list):
                    if self.rand:
                        value = random.choice(mapping)
                    else:
                        value = mapping[i]
                    res[field] = value
                elif callable(mapping):
                    res[field] = mapping(i)
                else:
                    res[field] = mapping
            self.resources.append(res)

    def generate_samples(self, dt):
        samples = []
        res_var = int(self.var_map.get_var(dt))
        for i in range(res_var):
            sample = copy.deepcopy(self.base_sample)
            sample['desc'] = self.resources[i]
            if self.vol_map:
                qty = self.vol_map.get_vol(dt)
                sample['vol']['qty'] = qty
            elif 'size' in sample['desc']:
                sample['vol']['qty'] = sample['desc']['size']
            # Packing
            sample['desc'] = json.dumps(self.resources[i])
            sample['vol'] = json.dumps(sample['vol'])

            samples.append(sample)
        return samples


class ComputeVarMapper(VariationMapper):
    var_map = {
        'mon': {
            'default': 1.0,
            12: 2.0,
            13: 3.0,
            14: 2.0,
            18: 2.0,
            19: 3.0,
            20: 4.0,
            21: 4.0,
            22: 3.0,
            23: 2.0,
            },
        'tue': {
            'default': 1.0,
            12: 2.0,
            13: 3.0,
            14: 2.0,
            18: 2.0,
            19: 3.0,
            20: 4.0,
            21: 4.0,
            22: 3.0,
            23: 2.0,
            },
        'wed': {
            'default': 1.0,
            12: 2.0,
            13: 3.0,
            14: 2.0,
            18: 2.0,
            19: 3.0,
            20: 4.0,
            21: 4.0,
            22: 3.0,
            23: 2.0,
        },
        'thu': {
            'default': 1.0,
            12: 2.0,
            13: 3.0,
            14: 2.0,
            18: 2.0,
            19: 3.0,
            20: 4.0,
            21: 4.0,
            22: 3.0,
            23: 2.0,
        },
        'fri': {
            'default': 1.0,
            12: 2.0,
            13: 3.0,
            14: 2.0,
            18: 2.0,
            19: 3.0,
            20: 4.0,
            21: 4.0,
            22: 3.0,
            23: 2.0,
        },
        'sat': {
            'default': 2.0,
            12: 3.0,
            13: 4.0,
            14: 3.0,
            18: 3.0,
            19: 4.0,
            20: 4.0,
            21: 4.0,
            22: 4.0,
            23: 3.0,
        },
        'sun': {
            'default': 2.0,
            12: 3.0,
            13: 4.0,
            14: 3.0,
            18: 3.0,
            19: 4.0,
            20: 4.0,
            21: 4.0,
            22: 4.0,
            23: 3.0,
        }}


class ComputeGenerator(BaseGenerator):
    base_sample = COMPUTE
    base_resource = COMPUTE_RESOURCE
    field_maps = {'flavor': 'flavors',
                  'image': 'images',
                  'name': 'generate_name',
                  'resource_id': 'res_id'}

    def init_mapper(self):
        self.flavors = {
            'm1.nano': {
                'vcpus': '1',
                'memory': '64'},
            'm1.micro': {
                'vcpus': '1',
                'memory': '128'}}
        self.images = []
        self.res_id = []
        for i in range(self.nb_res):
            self.res_id.append(str(uuid.uuid1()))

    def generate_name(self, *args):
        basename = 'instance{}'
        return basename.format(args[0])


class ImageGenerator(BaseGenerator):
    base_sample = IMAGE
    base_resource = IMAGE_RESOURCE
    field_maps = {'name': 'images'}
    rand = False

    def init_mapper(self):
        self.images = {
            'cirros-0.3.4-x86_64-uec-kernel': {
                'checksum': '836c69cbcd1dc4f225daedbab6edc7c7',
                'disk_format': 'ari',
                'container_format': 'ari',
                'size': '4969360',
                'resource_id': '5dd34048-6eeb-4b6c-aa51-62487733e5a1'},
            'cirros-0.3.4-x86_64-uec-ramdisk': {
                'checksum': '68085af2609d03e51c7662395b5b6e4b',
                'disk_format': 'aki',
                'container_format': 'aki',
                'size': '3723817',
                'resource_id': 'e512a97d-1ed5-4b27-a55a-1b9e5087936a'},
            'Fedora-x86_64-20-20131211.1-sda': {
                'checksum': '51bc16b900bf0f814bb6c0c3dd8f0790',
                'disk_format': 'qcow2',
                'container_format': 'bare',
                'size': '214106112',
                'resource_id': '3ee99f3f-7ecf-47b2-9a40-6df2d66ef5ae'}}


class VolumeGenerator(BaseGenerator):
    base_sample = VOLUME
    base_resource = VOLUME_RESOURCE
    field_maps = {'volume_id': 'volumes'}
    rand = False

    def init_mapper(self):
        self.volumes = {
            '2bed6a3d-468a-459b-802b-44930016c0a3': {
            'size': '10'},
            '4fd33321-6a5f-4351-94ca-db398cd708e9': {
            'size': '20'}}

    def generate_name(self, *args):
        basename = 'volume{}'
        return basename.format(args[0])


class NetBWVolMapper(VolumeVariationMapper):
    var_map = {
        'mon': {
            'default': 1024,
            12: 2048,
            13: 3072,
            14: 2048,
            18: 2048,
            19: 3072,
            20: 4096,
            21: 4096,
            22: 3072,
            23: 2048,
            },
        'tue': {
            'default': 1024,
            12: 2048,
            13: 3072,
            14: 2048,
            18: 2048,
            19: 3072,
            20: 4096,
            21: 4096,
            22: 3072,
            23: 2048,
            },
        'wed': {
            'default': 1024,
            12: 2048,
            13: 3072,
            14: 2048,
            18: 2048,
            19: 3072,
            20: 4096,
            21: 4096,
            22: 3072,
            23: 2048,
        },
        'thu': {
            'default': 1024,
            12: 2048,
            13: 3072,
            14: 2048,
            18: 2048,
            19: 3072,
            20: 4096,
            21: 4096,
            22: 3072,
            23: 2048,
        },
        'fri': {
            'default': 1024,
            12: 2048,
            13: 3072,
            14: 2048,
            18: 2048,
            19: 3072,
            20: 4096,
            21: 4096,
            22: 3072,
            23: 2048,
        },
        'sat': {
            'default': 2048,
            12: 3072,
            13: 4096,
            14: 3072,
            18: 3072,
            19: 4096,
            20: 4096,
            21: 4096,
            22: 4096,
            23: 3072,
        },
        'sun': {
            'default': 2048,
            12: 3072,
            13: 4096,
            14: 3072,
            18: 3072,
            19: 4096,
            20: 4096,
            21: 4096,
            22: 4096,
            23: 3072,
        }}


class NetworkBWGenerator(BaseGenerator):
    base_sample = NETWORK_BW_IN
    base_resource = NETWORK_BW_RESOURCE
    field_maps = {'instance_id': 'instances',
                  'name': 'generate_name',
                  'mac': 'generate_mac',
                  'resource_id': 'res_id'}
    rand = False

    def init_mapper(self):
        self.instances = []
        self.res_id = []
        for i in range(self.nb_res):
            self.res_id.append(str(uuid.uuid1()))

    def generate_name(self, *args):
        basename = 'tap{}-fc'
        return basename.format(args[0])

    def generate_mac(self, *args):
        basemac = 'fa:16:3e:{:0=2x}:{:0=2x}:{:0=2x}'
        return basemac.format(
            random.randint(1, 255),
            random.randint(1, 255),
            random.randint(1, 255))

    def generate_samples(self, dt):
        samples = []
        self.base_sample = NETWORK_BW_OUT
        samples.extend(super(NetworkBWGenerator, self).generate_samples(dt))
        self.base_sample = NETWORK_BW_IN
        samples.extend(super(NetworkBWGenerator, self).generate_samples(dt))
        return samples


class FloatingGenerator(BaseGenerator):
    base_sample = FLOATING
    base_resource = FLOATING_RESOURCE
    field_maps = {'fixed_ip_address': 'generate_ip_addr',
                  'floating_ip_address': 'generate_floating_addr',
                  'port_id': 'generate_port_id',
                  'resource_id': 'res_id',
                  'id': 'res_id'}
    rand = False

    def init_mapper(self):
        self.res_id = []
        for i in range(self.nb_res):
            self.res_id.append(str(uuid.uuid1()))

    def generate_name(self, *args):
        basename = 'volume{}'
        return basename.format(args[0])

    def generate_port_id(self, *args):
        return str(uuid.uuid1())

    def generate_ip_addr(self, *args):
        baseip = '10.0.0.{}'
        return baseip.format(random.randint(5, 250))

    def generate_floating_addr(self, *args):
        baseip = '172.24.4.{}'
        return baseip.format(random.randint(5, 250))


def write_samples(writer, dt, samples):
    for sample in samples:
        ts = calendar.timegm(dt.timetuple())
        sample['begin'] = ts
        sample['end'] = ts + 3600
        writer.writerow(sample)


def main():
    # Generators
    compute_var = ComputeVarMapper()
    image = ImageGenerator(3)
    image.generate_resources()
    volume = VolumeGenerator(2)
    volume.generate_resources()
    floating = FloatingGenerator(4, compute_var)
    floating.generate_resources()
    compute = ComputeGenerator(4, compute_var)
    compute.images = [resource['resource_id']
                      for resource in image.resources]
    compute.generate_resources()
    net_bw = NetworkBWGenerator(4, compute_var, NetBWVolMapper())
    net_bw.instances = [resource['resource_id']
                        for resource in compute.resources]
    net_bw.generate_resources()
    generators = [compute, image, volume, net_bw, floating]

    # Date
    now = datetime.datetime.utcnow()
    hour_delta = datetime.timedelta(hours=1)
    cur_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    cur_month = cur_date.month

    filename = sys.argv[1] if len(sys.argv) > 1 else 'generated.csv'
    with open(filename, 'wb') as csvfile:
        writer = csv.DictWriter(csvfile,
                                ['begin', 'end', 'type', 'desc', 'vol'])
        writer.writeheader()
        while cur_date.month == cur_month:
            for generator in generators:
                samples = generator.generate_samples(cur_date)
                write_samples(writer, cur_date, samples)
            cur_date += hour_delta


if __name__ == '__main__':
    main()
