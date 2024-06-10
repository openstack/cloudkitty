# Copyright (c) 2016, GohighSec
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

import ast
import re

from hacking import core


"""
Guidelines for writing new hacking checks

 - Use only for Cloudkitty specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range C3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the C3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to cloudkitty/tests/test_hacking.py

"""

UNDERSCORE_IMPORT_FILES = []

_all_log_levels = {'debug', 'error', 'info', 'warning',
                   'critical', 'exception'}
# Since _Lx have been removed, we just need to check _()
translated_logs = re.compile(
    r"(.)*LOG\.(%(level)s)\(\s*_\(" % {'level': '|'.join(_all_log_levels)})

string_translation = re.compile(r"[^_]*_\(\s*('|\")")
underscore_import_check = re.compile(r"(.)*import _$")
underscore_import_check_multi = re.compile(r"(.)*import (.)*_, (.)*")
# We need this for cases where they have created their own _ function.
custom_underscore_check = re.compile(r"(.)*_\s*=\s*(.)*")
oslo_namespace_imports = re.compile(r"from[\s]*oslo[.](.*)")
dict_constructor_with_list_copy_re = re.compile(r".*\bdict\((\[)?(\(|\[)")
assert_no_xrange_re = re.compile(r"\s*xrange\s*\(")
assert_True = re.compile(r".*assertEqual\(True, .*\)")
assert_None = re.compile(r".*assertEqual\(None, .*\)")
no_log_warn = re.compile(r".*LOG.warn\(.*\)")
asse_raises_regexp = re.compile(r"assertRaisesRegexp\(")


class BaseASTChecker(ast.NodeVisitor):
    """Provides a simple framework for writing AST-based checks.

    Subclasses should implement visit_* methods like any other AST visitor
    implementation. When they detect an error for a particular node the
    method should call ``self.add_error(offending_node)``. Details about
    where in the code the error occurred will be pulled from the node
    object.

    Subclasses should also provide a class variable named CHECK_DESC to
    be used for the human readable error message.

    """

    CHECK_DESC = 'No check message specified'

    def __init__(self, tree, filename):
        """This object is created automatically by pep8.

        :param tree: an AST tree
        :param filename: name of the file being analyzed
                         (ignored by our checks)
        """
        self._tree = tree
        self._errors = []

    def run(self):
        """Called automatically by pep8."""
        self.visit(self._tree)
        return self._errors

    def add_error(self, node, message=None):
        """Add an error caused by a node to the list of errors for pep8."""
        message = message or self.CHECK_DESC
        error = (node.lineno, node.col_offset, message, self.__class__)
        self._errors.append(error)

    def _check_call_names(self, call_node, names):
        if isinstance(call_node, ast.Call):
            if isinstance(call_node.func, ast.Name):
                if call_node.func.id in names:
                    return True
        return False


@core.flake8ext
def no_translate_logs(logical_line, filename):
    """Check for 'LOG.*(_('

    Starting with the Pike series, OpenStack no longer supports log
    translation.

    * This check assumes that 'LOG' is a logger.
    * Use filename so we can start enforcing this in specific folders instead
      of needing to do so all at once.

    C313
    """
    if translated_logs.match(logical_line):
        yield (0, "C313 Don't translate logs")


class CheckLoggingFormatArgs(BaseASTChecker):
    """Check for improper use of logging format arguments.

    LOG.debug("Volume %s caught fire and is at %d degrees C and climbing.",
              ('volume1', 500))

    The format arguments should not be a tuple as it is easy to miss.

    """

    name = "check_logging_format_args"
    version = "1.0"

    CHECK_DESC = 'C310 Log method arguments should not be a tuple.'
    LOG_METHODS = [
        'debug', 'info',
        'warn', 'warning',
        'error', 'exception',
        'critical', 'fatal',
        'trace', 'log'
    ]

    def _find_name(self, node):
        """Return the fully qualified name or a Name or Attribute."""
        if isinstance(node, ast.Name):
            return node.id
        elif (isinstance(node, ast.Attribute)
                and isinstance(node.value, (ast.Name, ast.Attribute))):
            method_name = node.attr
            obj_name = self._find_name(node.value)
            if obj_name is None:
                return None
            return obj_name + '.' + method_name
        elif isinstance(node, str):
            return node
        else:  # could be Subscript, Call or many more
            return None

    def visit_Call(self, node):
        """Look for the 'LOG.*' calls."""
        # extract the obj_name and method_name
        if isinstance(node.func, ast.Attribute):
            obj_name = self._find_name(node.func.value)
            if isinstance(node.func.value, ast.Name):
                method_name = node.func.attr
            elif isinstance(node.func.value, ast.Attribute):
                obj_name = self._find_name(node.func.value)
                method_name = node.func.attr
            else:  # could be Subscript, Call or many more
                return super(CheckLoggingFormatArgs, self).generic_visit(node)

            # obj must be a logger instance and method must be a log helper
            if (obj_name != 'LOG'
                    or method_name not in self.LOG_METHODS):
                return super(CheckLoggingFormatArgs, self).generic_visit(node)

            # the call must have arguments
            if not len(node.args):
                return super(CheckLoggingFormatArgs, self).generic_visit(node)

            # any argument should not be a tuple
            for arg in node.args:
                if isinstance(arg, ast.Tuple):
                    self.add_error(arg)

        return super(CheckLoggingFormatArgs, self).generic_visit(node)


@core.flake8ext
def check_explicit_underscore_import(logical_line, filename):
    """Check for explicit import of the _ function

    We need to ensure that any files that are using the _() function
    to translate logs are explicitly importing the _ function.  We
    can't trust unit test to catch whether the import has been
    added so we need to check for it here.
    """

    # Build a list of the files that have _ imported.  No further
    # checking needed once it is found.
    if filename in UNDERSCORE_IMPORT_FILES:
        pass
    elif (underscore_import_check.match(logical_line) or
          underscore_import_check_multi.match(logical_line) or
          custom_underscore_check.match(logical_line)):
        UNDERSCORE_IMPORT_FILES.append(filename)
    elif string_translation.match(logical_line):
        yield (0, "C321: Found use of _() without explicit import of _ !")


class CheckForStrUnicodeExc(BaseASTChecker):
    """Checks for the use of str() or unicode() on an exception.

    This currently only handles the case where str() or unicode()
    is used in the scope of an exception handler.  If the exception
    is passed into a function, returned from an assertRaises, or
    used on an exception created in the same scope, this does not
    catch it.
    """

    name = "check_for_str_unicode_exc"
    version = "1.0"

    CHECK_DESC = ('C314 str() and unicode() cannot be used on an '
                  'exception.  Remove it.')

    def __init__(self, tree, filename):
        super(CheckForStrUnicodeExc, self).__init__(tree, filename)
        self.name = []
        self.already_checked = []

    # Python 2
    def visit_TryExcept(self, node):
        for handler in node.handlers:
            if handler.name:
                self.name.append(handler.name.id)
                super(CheckForStrUnicodeExc, self).generic_visit(node)
                self.name = self.name[:-1]
            else:
                super(CheckForStrUnicodeExc, self).generic_visit(node)

    # Python 3
    def visit_ExceptHandler(self, node):
        if node.name:
            self.name.append(node.name)
            super(CheckForStrUnicodeExc, self).generic_visit(node)
            self.name = self.name[:-1]
        else:
            super(CheckForStrUnicodeExc, self).generic_visit(node)

    def visit_Call(self, node):
        if self._check_call_names(node, ['str', 'unicode']):
            if node not in self.already_checked:
                self.already_checked.append(node)
                if isinstance(node.args[0], ast.Name):
                    if node.args[0].id in self.name:
                        self.add_error(node.args[0])
        super(CheckForStrUnicodeExc, self).generic_visit(node)


class CheckForTransAdd(BaseASTChecker):
    """Checks for the use of concatenation on a translated string.

    Translations should not be concatenated with other strings, but
    should instead include the string being added to the translated
    string to give the translators the most information.
    """

    name = "check_for_trans_add"
    version = "1.0"

    CHECK_DESC = ('C315 Translated messages cannot be concatenated.  '
                  'String should be included in translated message.')

    TRANS_FUNC = ['_']

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Add):
            if self._check_call_names(node.left, self.TRANS_FUNC):
                self.add_error(node.left)
            elif self._check_call_names(node.right, self.TRANS_FUNC):
                self.add_error(node.right)
        super(CheckForTransAdd, self).generic_visit(node)


@core.flake8ext
def check_oslo_namespace_imports(logical_line, noqa):
    """'oslo_' should be used instead of 'oslo.'

    C317
    """
    if noqa:
        return
    if re.match(oslo_namespace_imports, logical_line):
        msg = ("C317: '%s' must be used instead of '%s'.") % (
            logical_line.replace('oslo.', 'oslo_'),
            logical_line)
        yield (0, msg)


@core.flake8ext
def dict_constructor_with_list_copy(logical_line):
    """Use a dict comprehension instead of a dict constructor

    C318
    """
    msg = ("C318: Must use a dict comprehension instead of a dict constructor"
           " with a sequence of key-value pairs."
           )
    if dict_constructor_with_list_copy_re.match(logical_line):
        yield (0, msg)


@core.flake8ext
def no_xrange(logical_line):
    """Ensure to not use xrange()

    C319
    """
    if assert_no_xrange_re.match(logical_line):
        yield (0, "C319: Do not use xrange().")


@core.flake8ext
def validate_assertTrue(logical_line):
    """Use assertTrue instead of assertEqual

    C312
    """
    if re.match(assert_True, logical_line):
        msg = ("C312: Unit tests should use assertTrue(value) instead"
               " of using assertEqual(True, value).")
        yield (0, msg)


@core.flake8ext
def validate_assertIsNone(logical_line):
    """Use assertIsNone instead of assertEqual

    C311
    """
    if re.match(assert_None, logical_line):
        msg = ("C311: Unit tests should use assertIsNone(value) instead"
               " of using assertEqual(None, value).")
        yield (0, msg)


@core.flake8ext
def no_log_warn_check(logical_line):
    """Disallow 'LOG.warn'

    C320
    """
    msg = ("C320: LOG.warn is deprecated, please use LOG.warning!")
    if re.match(no_log_warn, logical_line):
        yield (0, msg)


@core.flake8ext
def assert_raises_regexp(logical_line):
    """Check for usage of deprecated assertRaisesRegexp

    C322
    """
    res = asse_raises_regexp.search(logical_line)
    if res:
        yield (0, "C322: assertRaisesRegex must be used instead "
                  "of assertRaisesRegexp")
