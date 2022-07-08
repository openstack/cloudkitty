# Copyright 2019 Objectif Libre
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
from oslo_policy import policy

from cloudkitty.common.policies import base


scope_policies = [
    policy.DocumentedRuleDefault(
        name='scope:get_state',
        check_str=base.ROLE_ADMIN,
        description='Get the state of one or several scopes',
        operations=[{'path': '/v2/scope',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='scope:reset_state',
        check_str=base.ROLE_ADMIN,
        description='Reset the state of one or several scopes',
        operations=[{'path': '/v2/scope',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name='scope:patch_state',
        check_str=base.ROLE_ADMIN,
        description='Enables operators to patch a storage scope',
        operations=[{'path': '/v2/scope',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name='scope:post_state',
        check_str=base.ROLE_ADMIN,
        description='Enables operators to create a storage scope',
        operations=[{'path': '/v2/scope',
                     'method': 'POST'}]),
]


def list_rules():
    return scope_policies
