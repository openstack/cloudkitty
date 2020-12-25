# Copyright 2019 Objectif Libre
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
"""Common utils for voluptuous schema validation"""
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable
import functools
import voluptuous


class DictTypeValidator(object):
    """Voluptuous helper validating dict key and value types.

    When possible, keys and values will be converted to the required type.
    This behaviour can be disabled through the `cast` param.

    :param key_type: type of the dict keys
    :param value_type: type of the dict values
    :param cast: Set to False if you do not want to cast elements to the
                 required type.
    :type cast: bool
    :rtype: dict
    """

    def __init__(self, key_type, value_type, cast=True):
        if cast:
            self._kval = voluptuous.Coerce(key_type)
            self._vval = voluptuous.Coerce(value_type)
        else:
            def __type_validator(type_, elem):
                if not isinstance(elem, type_):
                    raise voluptuous.Invalid(
                        "{e} is not of type {t}".format(e=elem, t=type_))
                return elem

            self._kval = functools.partial(__type_validator, key_type)
            self._vval = functools.partial(__type_validator, value_type)

    def __call__(self, item):
        try:
            return {self._kval(k): self._vval(v)
                    for k, v in dict(item).items()}
        except (TypeError, ValueError):
            raise voluptuous.Invalid(
                "{} can't be converted to dict".format(item))


class IterableValuesDict(DictTypeValidator):
    """Voluptuous helper validating dicts with iterable values.

    When possible, keys and elements of values will be converted to the
    required type. This behaviour can be disabled through the `cast`
    param.

    :param key_type: type of the dict keys
    :param value_type: type of the dict values
    :param cast: Set to False if you do not want to convert elements to the
                 required type.
    :type cast: bool
    :rtype: dict
    """
    def __init__(self, key_type, value_type, cast=True):
        super(IterableValuesDict, self).__init__(key_type, value_type, cast)
        # NOTE(peschk_l): Using type(it) to return an iterable of the same
        # type as the passed argument.
        self.__vval = lambda it: type(it)(self._vval(i) for i in it)

    def __call__(self, item):
        try:
            for v in dict(item).values():
                if not isinstance(v, Iterable):
                    raise voluptuous.Invalid("{} is not iterable".format(v))

            return {self._kval(k): self.__vval(v) for k, v in item.items()}
        except (TypeError, ValueError) as e:
            raise voluptuous.Invalid(
                "{} can't be converted to a dict: {}".format(item, e))


def get_string_type():
    """Returns ``basestring`` in python2 and ``str`` in python3."""
    return str
