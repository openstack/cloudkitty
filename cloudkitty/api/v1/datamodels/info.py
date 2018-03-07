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
from oslo_config import cfg
from wsme import types as wtypes

from cloudkitty.default_metrics_conf import DEFAULT_METRICS_CONF
from cloudkitty import utils as ck_utils


CONF = cfg.CONF


def get_metrics_list():
    metrics_conf = ck_utils.get_metrics_conf(CONF.collect.metrics_conf)
    try:
        metrics = list(metrics_conf['metrics'].keys())
        cloudkitty_metrics = wtypes.Enum(wtypes.text, *metrics)
    except KeyError:
        metrics = list(DEFAULT_METRICS_CONF['metrics'].keys())
        cloudkitty_metrics = wtypes.Enum(wtypes.text, *metrics)

    return cloudkitty_metrics


class CloudkittyMetricInfo(wtypes.Base):
    """Type describing a metric info in CloudKitty."""

    metric_id = get_metrics_list()
    """Name of the metric."""

    metadata = [wtypes.text]
    """List of metric metadata"""

    unit = wtypes.text
    """Metric unit"""

    def to_json(self):
        res_dict = {}
        res_dict[self.metric_id] = [{
            'metadata': self.metadata,
            'unit': self.unit
        }]
        return res_dict

    @classmethod
    def sample(cls):
        metadata = ['resource_id', 'project_id', 'qty', 'unit']
        sample = cls(metric_id='image.size',
                     metadata=metadata,
                     unit='MiB')
        return sample


class CloudkittyMetricInfoCollection(wtypes.Base):
    """A list of CloudKittyMetricInfo."""

    metrics = [CloudkittyMetricInfo]

    @classmethod
    def sample(cls):
        sample = CloudkittyMetricInfo.sample()
        return cls(metrics=[sample])
