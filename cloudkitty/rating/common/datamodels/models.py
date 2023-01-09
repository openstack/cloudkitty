# -*- coding: utf-8 -*-
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
import datetime

from wsme import types as wtypes

from cloudkitty.api.v1 import types as ck_types


class VolatileAuditableModel(wtypes.Base):

    created_at = wtypes.wsattr(datetime.datetime, mandatory=False,
                               default=None)
    """The date the rule was created."""

    start = wtypes.wsattr(datetime.datetime, mandatory=False, default=None)
    """Must be None or a date in the future. To set a date in the past,
        use the force parameter in the POST query."""

    end = wtypes.wsattr(ck_types.EndDayDatetime(), mandatory=False,
                        default=None)
    """Must be None or a date in the future. To set a date in the past,
        use the force parameter in the POST query."""

    name = wtypes.wsattr(wtypes.text, mandatory=False, default=None)
    """The name of the rule."""

    description = wtypes.wsattr(wtypes.text, mandatory=False, default=None)
    """The description of the rule."""

    deleted = wtypes.wsattr(datetime.datetime, mandatory=False, default=None)
    """The date the rule was deleted."""

    created_by = wtypes.wsattr(wtypes.text, mandatory=False, default=None)
    """The id of the user who created the rule."""

    updated_by = wtypes.wsattr(wtypes.text, mandatory=False, default=None)
    """The id of the user who last updated the rule."""

    deleted_by = wtypes.wsattr(wtypes.text, mandatory=False, default=None)
    """The id of the user who deleted the rule."""

    @classmethod
    def sample(cls):
        sample = cls(created_at=datetime.datetime(2023, 1, 1, 10, 10, 10),
                     start=datetime.datetime(2023, 2, 1),
                     end=datetime.datetime(2023, 3, 1),
                     name='rule 1',
                     description='description',
                     deleted=datetime.datetime(2023, 1, 15),
                     created_by='7977999e2e2511e6a8b2df30b233ffcb',
                     updated_by='7977999e2e2511e6a8b2df30b233ffcb',
                     deleted_by='7977999e2e2511e6a8b2df30b233ffcb')
        return sample
