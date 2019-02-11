# Copyright 2017 GohighSec.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_policy import policy

from cloudkitty.common.policies import base

info_policies = [
    policy.DocumentedRuleDefault(
        name='info:list_services_info',
        check_str=base.UNPROTECTED,
        description='List available services information in Cloudkitty.',
        operations=[{'path': '/v1/info/services',
                     'method': 'LIST'}]),
    policy.DocumentedRuleDefault(
        name='info:get_service_info',
        check_str=base.UNPROTECTED,
        description='Get specified service information.',
        operations=[{'path': '/v1/info/services/{metric_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='info:list_metrics_info',
        check_str=base.UNPROTECTED,
        description='List available metrics information in Cloudkitty.',
        operations=[{'path': '/v1/info/metrics',
                     'method': 'LIST'}]),
    policy.DocumentedRuleDefault(
        name='info:get_metric_info',
        check_str=base.UNPROTECTED,
        description='Get specified metric information.',
        operations=[{'path': '/v1/info/metrics/{metric_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='info:get_config',
        check_str=base.UNPROTECTED,
        description='Get current configuration in Cloudkitty.',
        operations=[{'path': '/v1/info/config',
                     'method': 'GET'}])
]


def list_rules():
    return info_policies
