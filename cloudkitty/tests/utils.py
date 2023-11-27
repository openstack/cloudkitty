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
import copy
import random

from oslo_utils import uuidutils

from cloudkitty import dataframe
from cloudkitty.tests import samples


def generate_v2_storage_data(min_length=10,
                             nb_projects=2,
                             project_ids=None,
                             start=None,
                             end=None):

    if not project_ids:
        project_ids = [uuidutils.generate_uuid() for i in range(nb_projects)]
    elif not isinstance(project_ids, list):
        project_ids = [project_ids]

    df = dataframe.DataFrame(start=start, end=end)
    for metric_name, sample in samples.V2_STORAGE_SAMPLE.items():
        datapoints = []
        for project_id in project_ids:
            data = [copy.deepcopy(sample)
                    for i in range(min_length + random.randint(1, 10))]

            first_group = data[:round(len(data)/2)]
            second_group = data[round(len(data)/2):]

            for elem in first_group:
                elem['groupby']['year'] = 2022
                elem['groupby']['week_of_the_year'] = 1
                elem['groupby']['day_of_the_year'] = 1
                elem['groupby']['month'] = 10

            for elem in second_group:
                elem['groupby']['year'] = 2023
                elem['groupby']['week_of_the_year'] = 2
                elem['groupby']['day_of_the_year'] = 2
                elem['groupby']['month'] = 12

            data[0]['groupby']['year'] = 2021
            for elem in data:
                elem['groupby']['id'] = uuidutils.generate_uuid()
                elem['groupby']['project_id'] = project_id

            datapoints += [dataframe.DataPoint(
                elem['vol']['unit'],
                elem['vol']['qty'],
                elem['rating']['price'],
                elem['groupby'],
                elem['metadata'],
            ) for elem in data]
        df.add_points(datapoints, metric_name)

    return df


def load_conf(*args):
    return samples.DEFAULT_METRICS_CONF
