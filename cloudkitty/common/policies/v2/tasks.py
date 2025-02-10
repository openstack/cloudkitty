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


schedule_policies = [
    policy.DocumentedRuleDefault(
        name='schedule:task_reprocesses',
        check_str=base.ROLE_ADMIN,
        description='Schedule a scope for reprocessing',
        operations=[{'path': '/v2/task/reprocesses',
                     'method': 'POST'}],
        scope_types=['project']),
    policy.DocumentedRuleDefault(
        name='schedule:get_task_reprocesses',
        check_str=base.ROLE_ADMIN,
        description='Get reprocessing schedule tasks for scopes.',
        operations=[{'path': '/v2/task/reprocesses',
                     'method': 'GET'}],
        scope_types=['project']),
]


def list_rules():
    return schedule_policies
