# Copyright (c) 2011 OpenStack Foundation
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

# Borrowed from cinder (cinder/policy.py)

import copy
import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_policy import opts as policy_opts
from oslo_policy import policy
from oslo_utils import excutils
import six

from cloudkitty.common import policies

LOG = logging.getLogger(__name__)
CONF = cfg.CONF
policy_opts.set_defaults(cfg.CONF, 'policy.json')

_ENFORCER = None
# oslo_policy will read the policy configuration file again when the file
# is changed in runtime so the old policy rules will be saved to
# saved_file_rules and used to compare with new rules to determine the
# rules whether were updated.
saved_file_rules = []


# TODO(gpocentek): provide a proper parent class to handle such exceptions
class PolicyNotAuthorized(Exception):
    message = "Policy doesn't allow %(action)s to be performed."
    code = 403

    def __init__(self, **kwargs):
        self.msg = self.message % kwargs
        super(PolicyNotAuthorized, self).__init__(self.msg)

    def __unicode__(self):
        return six.text_type(self.msg)


def reset():
    global _ENFORCER
    if _ENFORCER:
        _ENFORCER.clear()
        _ENFORCER = None


def init():
    global _ENFORCER
    global saved_file_rules
    if not _ENFORCER:
        _ENFORCER = policy.Enforcer(CONF)
        register_rules(_ENFORCER)

    # Only the rules which are loaded from file may be changed.
    current_file_rules = _ENFORCER.file_rules
    current_file_rules = _serialize_rules(current_file_rules)

    # Checks whether the rules are updated in the runtime
    if saved_file_rules != current_file_rules:
        saved_file_rules = copy.deepcopy(current_file_rules)


def _serialize_rules(rules):
    """Serialize all the Rule object as string."""
    result = [(rule_name, str(rule))
              for rule_name, rule in rules.items()]
    return sorted(result, key=lambda rule: rule[0])


def authorize(context, action, target):
    """Verifies that the action is valid on the target in this context.

       :param context: cloudkitty context
       :param action: string representing the action to be checked
           this should be colon separated for clarity.
           i.e. ``compute:create_instance``,
           ``compute:attach_volume``,
           ``volume:attach_volume``

       :param object: dictionary representing the object of the action
           for object creation this should be a dictionary representing the
           location of the object e.g. ``{'project_id': context.project_id}``

       :raises PolicyNotAuthorized: if verification fails.

    """
    if CONF.auth_strategy != "keystone":
        return

    init()

    try:
        return _ENFORCER.authorize(action, target, context.to_dict(),
                                   do_raise=True,
                                   exc=PolicyNotAuthorized,
                                   action=action)

    except policy.PolicyNotRegistered:
        with excutils.save_and_reraise_exception():
            LOG.exception('Policy not registered')
    except Exception:
        with excutils.save_and_reraise_exception():
            LOG.error('Policy check for %(action)s failed with credentials '
                      '%(credentials)s',
                      {'action': action, 'credentials': context.to_dict()})


def check_is_admin(roles):
    """Whether or not roles contains 'admin' role according to policy setting.

    """
    if CONF.auth_strategy != "keystone":
        return True

    init()

    # include project_id on target to avoid KeyError if context_is_admin
    # policy definition is missing, and default admin_or_owner rule
    # attempts to apply.  Since our credentials dict does not include a
    # project_id, this target can never match as a generic rule.
    target = {'project_id': ''}
    credentials = {'roles': roles}

    return _ENFORCER.authorize('context_is_admin', target, credentials)


def register_rules(enforcer):
    enforcer.register_defaults(policies.list_rules())


def get_enforcer():
    # This method is for use by oslopolicy CLI scripts. Those scripts need the
    # 'output-file' and 'namespace' options, but having those in sys.argv means
    # loading the Cloudkitty config options will fail as those are not expected
    # to be present. So we pass in an arg list with those stripped out.
    conf_args = []
    # Start at 1 because cfg.CONF expects the equivalent of sys.argv[1:]
    i = 1
    while i < len(sys.argv):
        if sys.argv[i].strip('-') in ['namespace', 'output-file']:
            i += 2
            continue
        conf_args.append(sys.argv[i])
        i += 1

    cfg.CONF(conf_args, project='cloudkitty')
    init()
    return _ENFORCER
