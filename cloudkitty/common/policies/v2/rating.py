# Copyright 2019 Objectif Libre.
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

rating_policies = [
    policy.DocumentedRuleDefault(
        name='v2_rating:list_modules',
        check_str=base.ROLE_ADMIN,
        description='Returns the list of loaded modules in Cloudkitty.',
        operations=[{'path': '/v2/rating/modules',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='v2_rating:get_module',
        check_str=base.ROLE_ADMIN,
        description='Get specified module.',
        operations=[{'path': '/v2/rating/modules/{module_id}',
                     'method': 'GET'}]),
]


def list_rules():
    return rating_policies
