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


dataframes_policies = [
    policy.DocumentedRuleDefault(
        name='dataframes:add',
        check_str=base.ROLE_ADMIN,
        description='Add one or several DataFrames',
        operations=[{'path': '/v2/dataframes',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name='dataframes:get',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get DataFrames',
        operations=[{'path': '/v2/dataframes',
                     'method': 'GET'}]),
]


def list_rules():
    return dataframes_policies
