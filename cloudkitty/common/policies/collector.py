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

collector_policies = [
    policy.DocumentedRuleDefault(
        name='collector:list_mappings',
        check_str=base.ROLE_ADMIN,
        description='Return the list of every services mapped to a collector.',
        operations=[{'path': '/v1/collector/mappings',
                     'method': 'LIST'}]),
    policy.DocumentedRuleDefault(
        name='collector:get_mapping',
        check_str=base.ROLE_ADMIN,
        description='Return a service to collector mapping.',
        operations=[{'path': '/v1/collector/mappings/{service_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='collector:manage_mapping',
        check_str=base.ROLE_ADMIN,
        description='Manage a service to collector mapping.',
        operations=[{'path': '/v1/collector/mappings',
                     'method': 'POST'},
                    {'path': '/v1/collector/mappings/{service_id}',
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name='collector:get_state',
        check_str=base.ROLE_ADMIN,
        description='Query the enable state of a collector.',
        operations=[{'path': '/v1/collector/states/{collector_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='collector:update_state',
        check_str=base.ROLE_ADMIN,
        description='Set the enable state of a collector.',
        operations=[{'path': '/v1/collector/states/{collector_id}',
                     'method': 'PUT'}])
]


def list_rules():
    return collector_policies
