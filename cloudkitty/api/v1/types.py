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
# @author: Stéphane Albert
#
from oslo_utils import uuidutils
from wsme import types as wtypes


class UuidType(wtypes.UuidType):
    """A simple UUID type."""
    basetype = wtypes.text
    name = 'uuid'

    @staticmethod
    def validate(value):
        if not uuidutils.is_uuid_like(value):
            raise ValueError("Invalid UUID, got '%s'" % value)
        return value


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
