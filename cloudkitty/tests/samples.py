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
import copy
import datetime
import decimal

from oslo_utils import uuidutils

from cloudkitty import dataframe
from cloudkitty import utils as ck_utils

# These have a different format in order to check that both forms are supported
TENANT = 'f266f30b11f246b589fd266f85eeec39'
OTHER_TENANT = '8d3ae500-89ea-4142-9c6e-1269db6a0b64'

INITIAL_TIMESTAMP = 1420070400
FIRST_PERIOD_BEGIN = ck_utils.ts2dt(INITIAL_TIMESTAMP)
FIRST_PERIOD_BEGIN_ISO = ck_utils.dt2iso(FIRST_PERIOD_BEGIN)
FIRST_PERIOD_END = FIRST_PERIOD_BEGIN + datetime.timedelta(seconds=3600)
FIRST_PERIOD_END_ISO = ck_utils.dt2iso(FIRST_PERIOD_END)
SECOND_PERIOD_BEGIN = FIRST_PERIOD_END
SECOND_PERIOD_BEGIN_ISO = ck_utils.dt2iso(SECOND_PERIOD_BEGIN)
SECOND_PERIOD_END = SECOND_PERIOD_BEGIN + datetime.timedelta(seconds=3600)
SECOND_PERIOD_END_ISO = ck_utils.dt2iso(SECOND_PERIOD_END)

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
    'vcpus': '1'
}

COMPUTE_GROUPBY = {
    'id': '1558f911-b55a-4fd2-9173-c8f1f23e5639',
    'project_id': 'f266f30b11f246b589fd266f85eeec39',
    'user_id': '55b3379b949243009ee96972fbf51ed1',
}

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
    'updated_at': '2014-06-04T16:26:02',
}

IMAGE_GROUPBY = {
    'id': '7b5b73f2-9181-4307-a710-b1aa6472526d',
}

FIRST_PERIOD = {
    'begin': FIRST_PERIOD_BEGIN,
    'end': FIRST_PERIOD_END,
}

SECOND_PERIOD = {
    'begin': SECOND_PERIOD_BEGIN,
    'end': SECOND_PERIOD_END,
}

COLLECTED_DATA = [
    dataframe.DataFrame(start=FIRST_PERIOD["begin"],
                        end=FIRST_PERIOD["end"]),
    dataframe.DataFrame(start=SECOND_PERIOD["begin"],
                        end=SECOND_PERIOD["end"]),
]

_INSTANCE_POINT = dataframe.DataPoint(
    'instance', '1.0', '0.42', COMPUTE_GROUPBY, COMPUTE_METADATA)

_IMAGE_SIZE_POINT = dataframe.DataPoint(
    'image', '1.0', '0.1337', IMAGE_GROUPBY, IMAGE_METADATA)


COLLECTED_DATA[0].add_point(_INSTANCE_POINT, 'instance')
COLLECTED_DATA[0].add_point(_IMAGE_SIZE_POINT, 'image.size')
COLLECTED_DATA[1].add_point(_INSTANCE_POINT, 'instance')


RATED_DATA = copy.deepcopy(COLLECTED_DATA)

DEFAULT_METRICS_CONF = {
    "metrics": {
        "cpu": {
            "unit": "instance",
            "alt_name": "instance",
            "groupby": [
                "id",
                "project_id"
            ],
            "metadata": [
                "flavor",
                "flavor_id",
                "vcpus"
            ],
            "mutate": "NUMBOOL",
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "instance"
            }
        },
        "image.size": {
            "unit": "MiB",
            "factor": "1/1048576",
            "groupby": [
                "id",
                "project_id"
            ],
            "metadata": [
                "container_format",
                "disk_format"
            ],
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "image"
            }
        },
        "volume.size": {
            "unit": "GiB",
            "groupby": [
                "id",
                "project_id"
            ],
            "metadata": [
                "volume_type"
            ],
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "volume"
            }
        },
        "network.outgoing.bytes": {
            "unit": "MB",
            "groupby": [
                "id",
                "project_id"
            ],
            "factor": "1/1000000",
            "metadata": [
                "instance_id"
            ],
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "instance_network_interface"
            }
        },
        "network.incoming.bytes": {
            "unit": "MB",
            "groupby": [
                "id",
                "project_id"
            ],
            "factor": "1/1000000",
            "metadata": [
                "instance_id"
            ],
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "instance_network_interface"
            }
        },
        "ip.floating": {
            "unit": "ip",
            "groupby": [
                "id",
                "project_id"
            ],
            "metadata": [
                "state"
            ],
            "mutate": "NUMBOOL",
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "network"
            }
        },
        "radosgw.objects.size": {
            "unit": "GiB",
            "groupby": [
                "id",
                "project_id"
            ],
            "factor": "1/1073741824",
            "extra_args": {
                "aggregation_method": "max",
                "resource_type": "ceph_account"
            }
        }
    }
}


METRICS_CONF = DEFAULT_METRICS_CONF


PROMETHEUS_RESP_INSTANT_QUERY = {
    "status": "success",
    "data": {
        "resultType": "vector",
        "result": [
            {
                "metric": {
                    "code": "200",
                    "method": "get",
                    "group": "prometheus_group",
                    "instance": "localhost:9090",
                    "job": "prometheus",
                },
                "value": [
                    FIRST_PERIOD_END,
                    "7",
                ]
            },
            {
                "metric": {
                    "code": "200",
                    "method": "post",
                    "group": "prometheus_group",
                    "instance": "localhost:9090",
                    "job": "prometheus",
                },
                "value": [
                    FIRST_PERIOD_END,
                    "42",
                ]
            },

        ]
    }
}

PROMETHEUS_EMPTY_RESP_INSTANT_QUERY = {
    "status": "success",
    "data": {
        "resultType": "vector",
        "result": [],
    }
}

V2_STORAGE_SAMPLE = {
    "instance": {
        "vol": {
            "unit": "instance",
            "qty": 1.0,
        },
        "rating": {
            "price": decimal.Decimal(2.5),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "flavor": "m1.nano",
            "flavor_id": "42",
        },
    },
    "image.size": {
        "vol": {
            "unit": "MiB",
            "qty": 152.0,
        },
        "rating": {
            "price": decimal.Decimal(0.152),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "disk_format": "qcow2",
        },
    },
    "volume.size": {
        "vol": {
            "unit": "GiB",
            "qty": 20.0,
        },
        "rating": {
            "price": decimal.Decimal(1.2),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "volume_type": "ceph-region1"
        },
    },
    "network.outgoing.bytes": {
        "vol": {
            "unit": "MB",
            "qty": 12345.6,
        },
        "rating": {
            "price": decimal.Decimal(0.00123456),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "instance_id": uuidutils.generate_uuid(),
        },
    },
    "network.incoming.bytes": {
        "vol": {
            "unit": "MB",
            "qty": 34567.8,
        },
        "rating": {
            "price": decimal.Decimal(0.00345678),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "instance_id": uuidutils.generate_uuid(),
        },
    },
    "ip.floating": {
        "vol": {
            "unit": "ip",
            "qty": 1.0,
        },
        "rating": {
            "price": decimal.Decimal(0.01),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "state": "attached",
        },
    },
    "radosgw.objects.size": {
        "vol": {
            "unit": "GiB",
            "qty": 3.0,
        },
        "rating": {
            "price": decimal.Decimal(0.30),
        },
        "groupby": {
            "id": uuidutils.generate_uuid(),
            "project_id": COMPUTE_GROUPBY['project_id'],
        },
        "metadata": {
            "object_id": uuidutils.generate_uuid(),
        },
    }
}
