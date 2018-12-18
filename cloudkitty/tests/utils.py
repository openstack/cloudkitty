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
# @author: Luka Peschke
#
import copy
from datetime import datetime
import random

from oslo_utils import uuidutils

from cloudkitty.tests import samples
from cloudkitty import utils as ck_utils


def generate_v2_storage_data(min_length=10,
                             nb_projects=2,
                             project_ids=None,
                             start=datetime(2018, 1, 1),
                             end=datetime(2018, 1, 1, 1)):
    if isinstance(start, datetime):
        start = ck_utils.dt2ts(start)
    if isinstance(end, datetime):
        end = ck_utils.dt2ts(end)

    if not project_ids:
        project_ids = [uuidutils.generate_uuid() for i in range(nb_projects)]
    elif not isinstance(project_ids, list):
        project_ids = [project_ids]

    usage = {}
    for metric_name, sample in samples.V2_STORAGE_SAMPLE.items():
        dataframes = []
        for project_id in project_ids:
            data = [copy.deepcopy(sample)
                    for i in range(min_length + random.randint(1, 10))]
            for elem in data:
                elem['groupby']['id'] = uuidutils.generate_uuid()
                elem['groupby']['project_id'] = project_id
            dataframes += data
        usage[metric_name] = dataframes

    return {
        'usage': usage,
        'period': {
            'begin': start,
            'end': end
        }
    }


def load_conf(*args):
    return samples.DEFAULT_METRICS_CONF
