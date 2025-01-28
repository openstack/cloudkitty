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

RULE_ADMIN_OR_OWNER = 'rule:admin_or_owner'
ROLE_ADMIN = 'role:admin'
UNPROTECTED = ''

DEPRECATED_REASON = """
CloudKitty API policies are introducing new default roles with scope_type
capabilities. Old policies are deprecated and silently going to be ignored
in future release.
"""

DEPRECATED_ADMIN_OR_OWNER_POLICY = policy.DeprecatedRule(
    name=RULE_ADMIN_OR_OWNER,
    check_str='is_admin:True or '
              '(role:admin and is_admin_project:True) or '
              'project_id:%(project_id)s',
    deprecated_reason=DEPRECATED_REASON,
    deprecated_since='22.0.0'
)

PROJECT_MEMBER_OR_ADMIN = 'rule:project_member_or_admin'
PROJECT_READER_OR_ADMIN = 'rule:project_reader_or_admin'

rules = [
    policy.RuleDefault(
        name='context_is_admin',
        check_str='role:admin'),
    policy.RuleDefault(
        name='admin_or_owner',
        check_str='is_admin:True or '
                  '(role:admin and is_admin_project:True) or '
                  'project_id:%(project_id)s',
        deprecated_for_removal=True,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since='22.0.0'),
    policy.RuleDefault(
        name='default',
        check_str=UNPROTECTED),
    policy.RuleDefault(
        "project_member_api",
        "role:member and project_id:%(project_id)s",
        "Default rule for Project level non admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "project_reader_api",
        "role:reader and project_id:%(project_id)s",
        "Default rule for Project level read only APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "project_member_or_admin",
        "rule:project_member_api or rule:context_is_admin",
        "Default rule for Project Member or admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY),
    policy.RuleDefault(
        "project_reader_or_admin",
        "rule:project_reader_api or rule:context_is_admin",
        "Default rule for Project reader or admin APIs.",
        deprecated_rule=DEPRECATED_ADMIN_OR_OWNER_POLICY)
]


def list_rules():
    return rules
