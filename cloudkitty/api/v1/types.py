# -*- coding: utf-8 -*-
# Copyright 2014 Objectif Libre
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

from oslo_log import log as logging
from oslo_utils import uuidutils
from wsme.rest.json import tojson
from wsme import types as wtypes


LOG = logging.getLogger(__name__)


class UuidType(wtypes.UuidType):
    """A simple UUID type."""
    basetype = wtypes.text
    name = 'uuid'

    @staticmethod
    def validate(value):
        if not uuidutils.is_uuid_like(value):
            raise ValueError("Invalid UUID, got '%s'" % value)
        return value


class EndDayDatetimeBaseType(datetime.datetime):
    pass


@tojson.when_object(EndDayDatetimeBaseType)
def datetime_end_day_tojson(datatype, value):
    if value is None:
        return None
    return value.isoformat()


class EndDayDatetime(wtypes.UserType):
    basetype = EndDayDatetimeBaseType
    name = 'end'

    def validate(self, value):
        if isinstance(value, datetime.datetime):
            return value

        token_that_splits_date_from_time_in_iso_format = 'T'

        if token_that_splits_date_from_time_in_iso_format in value:
            LOG.debug("There is a time in the end date [%s]; "
                      "therefore, we will maintain the time, "
                      "and use the datetime as is.", value)

            return datetime.datetime.fromisoformat(value)

        LOG.debug("The end date [%s] was not defined with a specific time, "
                  "using time [23:59:59] as end time.", value)

        dt = datetime.datetime.fromisoformat(value)
        return datetime.datetime(
            year=dt.year, month=dt.month, day=dt.day,
            hour=23, minute=59, second=59)


# Code taken from ironic types
class MultiType(wtypes.UserType):
    """A complex type that represents one or more types.

    Used for validating that a value is an instance of one of the types.

    :param *types: Variable-length list of types.

    """
    def __init__(self, *types):
        self.types = types

    def __str__(self):
        return ' | '.join(map(str, self.types))

    def validate(self, value):
        for t in self.types:
            if t is wtypes.text and isinstance(value, wtypes.bytes):
                value = value.decode()
            if isinstance(value, t):
                return value
        else:
            raise ValueError(
                "Wrong type. Expected '%(type)s', got '%(value)s'"
                % {'type': self.types, 'value': type(value)})
