# Copyright (c) 2017 GohighSec.
# All Rights Reserved.
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
import os.path
import testtools

from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_context import context
from oslo_policy import policy as oslo_policy

from cloudkitty.common import policy
from cloudkitty import tests
from cloudkitty.tests.utils import is_functional_test
from cloudkitty import utils


CONF = cfg.CONF


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class PolicyFileTestCase(tests.TestCase):

    def setUp(self):
        super(PolicyFileTestCase, self).setUp()
        self.context = context.RequestContext('fake', 'fake', roles=['member'])
        self.target = {}
        self.fixture = self.useFixture(config_fixture.Config(CONF))
        self.addCleanup(policy.reset)
        CONF(args=[], project='cloudkitty', default_config_files=[])

    def test_modified_policy_reloads(self):
        with utils.tempdir() as tmpdir:
            tmpfilename = os.path.join(tmpdir, 'policy')
            self.fixture.config(policy_file=tmpfilename, group='oslo_policy')
            rule = oslo_policy.RuleDefault('example:test', "")
            policy.reset()
            policy.init()
            policy._ENFORCER.register_defaults([rule])

            action = "example:test"
            with open(tmpfilename, "w") as policyfile:
                policyfile.write('{"example:test": ""}')
            policy.authorize(self.context, action, self.target)
            with open(tmpfilename, "w") as policyfile:
                policyfile.write('{"example:test": "!"}')
            policy._ENFORCER.load_rules(True)
            self.assertRaises(policy.PolicyNotAuthorized,
                              policy.authorize,
                              self.context, action, self.target)


@testtools.skipIf(is_functional_test(), 'Not a functional test')
class PolicyTestCase(tests.TestCase):

    def setUp(self):
        super(PolicyTestCase, self).setUp()
        rules = [
            oslo_policy.RuleDefault("true", '@'),
            oslo_policy.RuleDefault("test:allowed", '@'),
            oslo_policy.RuleDefault("test:denied", "!"),
            oslo_policy.RuleDefault("test:early_and_fail", "! and @"),
            oslo_policy.RuleDefault("test:early_or_success", "@ or !"),
            oslo_policy.RuleDefault("test:lowercase_admin",
                                    "role:admin"),
            oslo_policy.RuleDefault("test:uppercase_admin",
                                    "role:ADMIN"),
        ]
        CONF(args=[], project='cloudkitty', default_config_files=[])
        # before a policy rule can be used, its default has to be registered.
        policy.reset()
        policy.init()
        policy._ENFORCER.register_defaults(rules)
        self.context = context.RequestContext('fake',
                                              'fake',
                                              roles=['member'])
        self.target = {}
        self.addCleanup(policy.reset)

    def test_enforce_nonexistent_action_throws(self):
        action = "test:noexist"
        self.assertRaises(oslo_policy.PolicyNotRegistered, policy.authorize,
                          self.context, action, self.target)

    def test_enforce_bad_action_throws(self):
        action = "test:denied"
        self.assertRaises(policy.PolicyNotAuthorized, policy.authorize,
                          self.context, action, self.target)

    def test_enforce_bad_action_noraise(self):
        action = "test:denied"
        self.assertRaises(policy.PolicyNotAuthorized, policy.authorize,
                          self.context, action, self.target)

    def test_enforce_good_action(self):
        action = "test:allowed"
        result = policy.authorize(self.context, action, self.target)
        self.assertTrue(result)

    def test_early_AND_authorization(self):
        action = "test:early_and_fail"
        self.assertRaises(policy.PolicyNotAuthorized, policy.authorize,
                          self.context, action, self.target)

    def test_early_OR_authorization(self):
        action = "test:early_or_success"
        policy.authorize(self.context, action, self.target)

    def test_ignore_case_role_check(self):
        lowercase_action = "test:lowercase_admin"
        uppercase_action = "test:uppercase_admin"
        admin_context = context.RequestContext('admin',
                                               'fake',
                                               roles=['AdMiN'])
        policy.authorize(admin_context, lowercase_action, self.target)
        policy.authorize(admin_context, uppercase_action, self.target)
