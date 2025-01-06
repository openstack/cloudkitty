#    Copyright 2016 GohighSec
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

import textwrap
from unittest import mock

import ddt
import pycodestyle

from cloudkitty.hacking import checks
from cloudkitty import tests


@ddt.ddt
class HackingTestCase(tests.TestCase):
    """Hacking test cases

    This class tests the hacking checks in cloudkitty.hacking.checks by passing
    strings to the check methods like the pep8/flake8 parser would. The parser
    loops over each line in the file and then passes the parameters to the
    check method. The parameter names in the check method dictate what type of
    object is passed to the check method. The parameter types are::

        logical_line: A processed line with the following modifications:
            - Multi-line statements converted to a single line.
            - Stripped left and right.
            - Contents of strings replaced with "xxx" of same length.
            - Comments removed.
        physical_line: Raw line of text from the input file.
        lines: a list of the raw lines from the input file
        tokens: the tokens that contribute to this logical line
        line_number: line number in the input file
        total_lines: number of lines in the input file
        blank_lines: blank lines before this one
        indent_char: indentation character in this file (" " or "\t")
        indent_level: indentation (with tabs expanded to multiples of 8)
        previous_indent_level: indentation on previous line
        previous_logical: previous logical line
        filename: Path of the file being run through pep8

    When running a test on a check method the return will be False/None if
    there is no violation in the sample input. If there is an error a tuple is
    returned with a position in the line, and a message. So to check the result
    just assertTrue if the check is expected to fail and assertFalse if it
    should pass.
    """

    def test_no_log_translations(self):
        for log in checks._all_log_levels:
            bad = 'LOG.%s(_("Bad"))' % log
            self.assertEqual(1, len(list(checks.no_translate_logs(bad, 'f'))))
            # Catch abuses when used with a variable and not a literal
            bad = 'LOG.%s(_(msg))' % log
            self.assertEqual(1, len(list(checks.no_translate_logs(bad, 'f'))))

    def test_check_explicit_underscore_import(self):
        self.assertEqual(1, len(list(checks.check_explicit_underscore_import(
            "LOG.info(_('My info message'))",
            "cloudkitty/tests/other_files.py"))))
        self.assertEqual(1, len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "cloudkitty/tests/other_files.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "from cloudkitty.i18n import _",
            "cloudkitty/tests/other_files.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "LOG.info(_('My info message'))",
            "cloudkitty/tests/other_files.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "cloudkitty/tests/other_files.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "from cloudkitty.i18n import _",
            "cloudkitty/tests/other_files2.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "cloudkitty/tests/other_files2.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "_ = translations.ugettext",
            "cloudkitty/tests/other_files3.py"))))
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "cloudkitty/tests/other_files3.py"))))
        # Complete code coverage by falling through all checks
        self.assertEqual(0, len(list(checks.check_explicit_underscore_import(
            "LOG.info('My info message')",
            "cloudkitty.tests.unit/other_files4.py"))))
        self.assertEqual(1, len(list(checks.check_explicit_underscore_import(
            "msg = _('My message')",
            "cloudkitty.tests.unit/other_files5.py"))))

    # We are patching pep8 so that only the check under test is actually
    # installed.
    @mock.patch('pycodestyle._checks',
                {'physical_line': {}, 'logical_line': {}, 'tree': {}})
    def _run_check(self, code, checker, filename=None):
        pycodestyle.register_check(checker)

        lines = textwrap.dedent(code).strip().splitlines(True)

        checker = pycodestyle.Checker(filename=filename, lines=lines)
        checker.check_all()
        checker.report._deferred_print.sort()
        return checker.report._deferred_print

    def _assert_has_errors(self, code, checker, expected_errors=None,
                           filename=None):
        actual_errors = [e[:3] for e in
                         self._run_check(code, checker, filename)]
        self.assertEqual(expected_errors or [], actual_errors)

    def _assert_has_no_errors(self, code, checker, filename=None):
        self._assert_has_errors(code, checker, filename=filename)

    def test_logging_format_no_tuple_arguments(self):
        checker = checks.CheckLoggingFormatArgs
        code = """
               import logging
               LOG = logging.getLogger()
               LOG.info("Message without a second argument.")
               LOG.critical("Message with %s arguments.", 'two')
               LOG.debug("Volume %s caught fire and is at %d degrees C and"
                         " climbing.", 'volume1', 500)
               """
        self._assert_has_no_errors(code, checker)

    @ddt.data(*checks.CheckLoggingFormatArgs.LOG_METHODS)
    def test_logging_with_tuple_argument(self, log_method):
        checker = checks.CheckLoggingFormatArgs
        code = """
               import logging
               LOG = logging.getLogger()
               LOG.{0}("Volume %s caught fire and is at %d degrees C and "
                      "climbing.", ('volume1', 500))
               """
        self._assert_has_errors(code.format(log_method), checker,
                                expected_errors=[(4, mock.ANY, 'C310')])

    def test_str_on_exception(self):

        checker = checks.CheckForStrUnicodeExc
        code = """
               def f(a, b):
                   try:
                       p = str(a) + str(b)
                   except ValueError as e:
                       p = str(e)
                   return p
               """
        errors = [(5, mock.ANY, 'C314')]
        self._assert_has_errors(code, checker, expected_errors=errors)

    def test_no_str_unicode_on_exception(self):
        checker = checks.CheckForStrUnicodeExc
        code = """
               def f(a, b):
                   try:
                       p = unicode(a) + str(b)
                   except ValueError as e:
                       p = e
                   return p
               """
        self._assert_has_no_errors(code, checker)

    def test_unicode_on_exception(self):
        checker = checks.CheckForStrUnicodeExc
        code = """
               def f(a, b):
                   try:
                       p = str(a) + str(b)
                   except ValueError as e:
                       p = unicode(e)
                   return p
               """
        errors = [(5, mock.ANY, 'C314')]
        self._assert_has_errors(code, checker, expected_errors=errors)

    def test_str_on_multiple_exceptions(self):
        checker = checks.CheckForStrUnicodeExc
        code = """
               def f(a, b):
                   try:
                       p = str(a) + str(b)
                   except ValueError as e:
                       try:
                           p  = unicode(a) + unicode(b)
                       except ValueError as ve:
                           p = str(e) + str(ve)
                       p = e
                   return p
               """
        errors = [(8, mock.ANY, 'C314'), (8, mock.ANY, 'C314')]
        self._assert_has_errors(code, checker, expected_errors=errors)

    def test_str_unicode_on_multiple_exceptions(self):
        checker = checks.CheckForStrUnicodeExc
        code = """
               def f(a, b):
                   try:
                       p = str(a) + str(b)
                   except ValueError as e:
                       try:
                           p  = unicode(a) + unicode(b)
                       except ValueError as ve:
                           p = str(e) + unicode(ve)
                       p = str(e)
                   return p
               """
        errors = [(8, mock.ANY, 'C314'),
                  (8, mock.ANY, 'C314'),
                  (9, mock.ANY, 'C314')]
        self._assert_has_errors(code, checker, expected_errors=errors)

    def test_trans_add(self):

        checker = checks.CheckForTransAdd
        code = """
               def fake_tran(msg):
                   return msg


               _ = fake_tran


               def f(a, b):
                   msg = _('test') + 'add me'
                   msg = 'add to me' + _('test')
                   return msg
               """

        # We don't assert on specific column numbers since there is a small
        # change in calculation between <py38 and >=py38
        errors = [(9, mock.ANY, 'C315'), (10, mock.ANY, 'C315')]
        self._assert_has_errors(code, checker, expected_errors=errors)

        code = """
               def f(a, b):
                   msg = 'test' + 'add me'
                   return msg
               """
        errors = []
        self._assert_has_errors(code, checker, expected_errors=errors)

    def test_dict_constructor_with_list_copy(self):
        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "    dict([(i, connect_info[i])"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "    attrs = dict([(k, _from_json(v))"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "        type_names = dict((value, key) for key, value in"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "   dict((value, key) for key, value in"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "foo(param=dict((k, v) for k, v in bar.items()))"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            " dict([[i,i] for i in range(3)])"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "  dd = dict([i,i] for i in range(3))"))))

        self.assertEqual(0, len(list(checks.dict_constructor_with_list_copy(
            "        create_kwargs = dict(snapshot=snapshot,"))))

        self.assertEqual(0, len(list(checks.dict_constructor_with_list_copy(
            "      self._render_dict(xml, data_el, data.__dict__)"))))

    def test_no_xrange(self):
        self.assertEqual(1, len(list(checks.no_xrange("xrange(45)"))))

        self.assertEqual(0, len(list(checks.no_xrange("range(45)"))))

    def test_no_log_warn_check(self):
        self.assertEqual(0, len(list(checks.no_log_warn_check(
            "LOG.warning('This should not trigger LOG.warn"
            "hacking check.')"))))
        self.assertEqual(1, len(list(checks.no_log_warn_check(
            "LOG.warn('We should not use LOG.wan')"))))
