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

report_policies = [
    policy.DocumentedRuleDefault(
        name='report:list_tenants',
        check_str=base.ROLE_ADMIN,
        description='Return the list of rated tenants.',
        operations=[{'path': '/v1/report/tenants',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='report:get_summary',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Return the summary to pay for a given period.',
        operations=[{'path': '/v1/report/summary',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name='report:get_total',
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Return the amount to pay for a given period.',
        operations=[{'path': '/v1/report/total',
                     'method': 'GET'}])
]


def list_rules():
    return report_policies
