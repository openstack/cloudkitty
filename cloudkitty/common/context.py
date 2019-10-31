# Copyright 2019 Objectif Libre
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
#
from oslo_context import context

from cloudkitty.common import policy


class RequestContext(context.RequestContext):

    def __init__(self, is_admin=None, **kwargs):
        super(RequestContext, self).__init__(is_admin=is_admin, **kwargs)
        if self.is_admin is None:
            self.is_admin = policy.check_is_admin(self)
