# Copyright 2018 Objectif Libre
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
import sys

from oslo_config import cfg
from oslo_upgradecheck import common_checks
from oslo_upgradecheck import upgradecheck

from cloudkitty.i18n import _
# Import needed to register storage options
from cloudkitty import storage  # noqa


CONF = cfg.CONF


class CloudkittyUpgradeChecks(upgradecheck.UpgradeCommands):

    def _storage_version(self):
        if CONF.storage.version < 2:
            return upgradecheck.Result(
                upgradecheck.Code.WARNING,
                'Storage version is inferior to 2. Support for v1 storage '
                'will be dropped in a future release.',
            )
        return upgradecheck.Result(upgradecheck.Code.SUCCESS)

    _upgrade_checks = (
        (_('Storage version'), _storage_version),
        (_("Policy File JSON to YAML Migration"),
         (common_checks.check_policy_json, {'conf': CONF})),
    )


def main():
    return upgradecheck.main(
        conf=CONF,
        project='cloudkitty',
        upgrade_command=CloudkittyUpgradeChecks(),
    )


if __name__ == '__main__':
    sys.exit(main())
