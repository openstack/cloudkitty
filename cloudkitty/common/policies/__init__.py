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

import itertools

from cloudkitty.common.policies import base
from cloudkitty.common.policies.v1 import collector as v1_collector
from cloudkitty.common.policies.v1 import info as v1_info
from cloudkitty.common.policies.v1 import rating as v1_rating
from cloudkitty.common.policies.v1 import report as v1_report
from cloudkitty.common.policies.v1 import storage as v1_storage
from cloudkitty.common.policies.v2 import dataframes as v2_dataframes
from cloudkitty.common.policies.v2 import rating as v2_rating
from cloudkitty.common.policies.v2 import scope as v2_scope
from cloudkitty.common.policies.v2 import summary as v2_summary
from cloudkitty.common.policies.v2 import tasks as v2_tasks


def list_rules():
    return itertools.chain(
        base.list_rules(),
        v1_collector.list_rules(),
        v1_info.list_rules(),
        v1_rating.list_rules(),
        v1_report.list_rules(),
        v1_storage.list_rules(),
        v2_dataframes.list_rules(),
        v2_rating.list_rules(),
        v2_scope.list_rules(),
        v2_summary.list_rules(),
        v2_tasks.list_rules()
    )
