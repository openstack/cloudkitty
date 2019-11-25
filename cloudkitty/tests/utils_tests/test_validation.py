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
import unittest

import voluptuous.error

from cloudkitty.utils import validation as validation_utils


class DictTypeValidatorTest(unittest.TestCase):

    def test_dictvalidator_valid_dict_with_cast(self):
        validator = validation_utils.DictTypeValidator(str, str)
        self.assertEqual(validator({'a': '1', 'b': 2}), {'a': '1', 'b': '2'})

    def test_dictvalidator_valid_dict_without_cast(self):
        validator = validation_utils.DictTypeValidator(str, str, cast=False)
        self.assertEqual(validator({'a': '1', 'b': '2'}), {'a': '1', 'b': '2'})

    def test_dictvalidator_invalid_dict_without_cast(self):
        validator = validation_utils.DictTypeValidator(str, str, cast=False)
        self.assertRaises(
            voluptuous.error.Invalid, validator, {'a': '1', 'b': 2})

    def test_dictvalidator_invalid_dict_with_cast(self):
        validator = validation_utils.DictTypeValidator(str, int)
        self.assertRaises(
            voluptuous.error.Invalid, validator, {'a': '1', 'b': 'aa'})

    def test_dictvalidator_invalid_type_tuple(self):
        validator = validation_utils.DictTypeValidator(str, int)
        self.assertRaises(
            voluptuous.error.Invalid, validator, ('a', '1'))

    def test_dictvalidator_invalid_type_str(self):
        validator = validation_utils.DictTypeValidator(str, int)
        self.assertRaises(
            voluptuous.error.Invalid, validator, 'aaaa')


class IterableValuesDictTest(unittest.TestCase):

    def test_iterablevaluesdict_valid_list_and_tuple_with_cast(self):
        validator = validation_utils.IterableValuesDict(str, str)
        self.assertEqual(
            validator({'a': [1, '2'], 'b': ('3', 4)}),
            {'a': ['1', '2'], 'b': ('3', '4')},
        )

    def test_iterablevaluesdict_valid_list_and_tuple_without_cast(self):
        validator = validation_utils.IterableValuesDict(str, str)
        self.assertEqual(
            validator({'a': ['1', '2'], 'b': ('3', '4')}),
            {'a': ['1', '2'], 'b': ('3', '4')},
        )

    def test_iterablevaluesdict_invalid_dict_iterable_without_cast(self):
        validator = validation_utils.IterableValuesDict(str, str, cast=False)
        self.assertRaises(
            voluptuous.error.Invalid, validator, {'a': ['1'], 'b': (2, )})

    def test_iterablevaluesdict_invalid_dict_iterable_with_cast(self):
        validator = validation_utils.IterableValuesDict(str, int, cast=False)
        self.assertRaises(
            voluptuous.error.Invalid, validator, {'a': ['1'], 'b': ('aa', )})

    def test_iterablevaluesdict_invalid_iterable_with_cast(self):
        validator = validation_utils.IterableValuesDict(str, int)
        self.assertRaises(
            voluptuous.error.Invalid, validator, {'a': ['1'], 'b': 42, })

    def test_iterablevaluesdict_invalid_type_tuple(self):
        validator = validation_utils.IterableValuesDict(str, int)
        self.assertRaises(
            voluptuous.error.Invalid, validator, ('a', '1'))

    def test_iterablevaluesdict_invalid_type_str(self):
        validator = validation_utils.IterableValuesDict(str, int)
        self.assertRaises(
            voluptuous.error.Invalid, validator, 'aaaa')
