#
# Copyright (C) 2015 Prevas A/S
#
# This file is part of dtest, an embedded device test framework
#
# dtest is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# dtest is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
# more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

#
# A suite can be given arguments in the form of an yaml associative array like this:
#
#            mytest: { count: 4, params: { min: 12 } }
#
# Suite arguments:
#
#   params:   An associative array defining parameters given to the testcase
#
#   count:    A number specifying the number of times to 'run' the testcase
#
#   id:       By default a testcase is assigned a result and a tmp directory having the
#             the name of the testcase itself (possibly extended with a number to
#             become unique). This argument can be used to assign an alternative name
#
#   cfg_idx:  Index of the dctrl config file to use. Default is to use index 0.
#             Dctrl configs are defined in dtest.conf in a DctrlConfigs list
#
#   exit-on-error:
#             When set on a suite the suite will bail out if any of the 'sub-suites'
#             fails.
#
#   flag:     The value assigned to a flag will be written 'as is' to the result file.
#             The flag has no impact on the testrun but is considered a means of
#             signalling information to a post-processing task.
#
#   type:     A key-value pair written as is to the result file. Valid values are
#                  'setup', teardown' or 'suite'
#
#   setup:    Indicates the step is considered part of the setup.
#
#   teardown: Indicates the step is considered part of the teardown.
#
#   name:     By default a tests name is the 'key' (like dctr.linux.cmd). Using the
#             name key an alternative name can be given. The name is written into
#             the result file
#
#   expect:   By default a test is supposed to pass. By setting expect to 'fail'
#             a failing test won't count as an error. (But it will if it passes)
#

import unittest
import logging
import sys
import os
import yaml
import re
import types
from testsetup import testsetup
import dtest
import dtestsuite
import copy
import itertools

logger = logging.getLogger("dtest")

class DTestLoader(unittest.TestLoader):

    def __init__(self, path=None, overlays=[]):
        if isinstance(path, list):
            self.path = path
        elif isinstance(path, basestring):
            self.path = [ os.path.abspath(path) ]
        else:
            assert path is None
            self.path = [ os.getcwd() ]
        if overlays:
            self.overlays = overlays
        else:
            self.overlays = []
        self.logger = dtest.logger
        self.logger.debug("Overlays are: %s"%(self.overlays))

        self.testsetup = testsetup()
        self.suiteClass = dtestsuite.DtestTestSuite
        super(DTestLoader, self).__init__()

    def validateTestArgs(self,testcaseargs):
        """
        Validate the arguments
        If they are not valid then an exception is raised
        """
        # count and retry are mutual exclusive
        if 'count' in testcaseargs and 'retry' in testcaseargs:
            raise TypeError('only specify one of count and retry')

        if 'retry' in testcaseargs:
            retry=testcaseargs['retry']
            if not isinstance( retry, (int, long ) ):
                raise TypeError('retry parameter is not int as expected')
            if retry < 2:
                raise TypeError('ERROR: retry parameter is less than 2 - mistake?')

        if 'count' in testcaseargs:
            count=testcaseargs['count']
            if not isinstance( count, (int, long ) ):
                raise TypeError('count parameter is not int as expected')
            if count < 2:
                raise TypeError('ERROR: count parameter is less than 2 - mistake?')

    def updateSuiteParams(self,yamlstring,suiteparams):
        def findNextWhitespace(s,begin):
            count = 0
            for n in s[begin:]:
                if(n in string.whitespace):
                    return begin+count
                else:
                    count+=1

        def findNextToken(s,begin):
            count = 0
            for n in s[begin:]:
                if(n in string.whitespace):
                    count += 1
                else:
                    return begin+count

        def findNextChar(s,begin,token):
            count = 0
            for n in s[begin:]:
                if n == token:
                     return begin+count+1
                else:
                    count += 1

        import string
        i=0
        newstring=""
        while(not yamlstring.find("&",i) == -1):
            anchor = yamlstring.find("&",i)
            #value starts after next whitespace(s)
            nextw = findNextWhitespace(yamlstring,anchor)
            valb = findNextToken(yamlstring,nextw)
            key = yamlstring[anchor+1:nextw]
            #add up until after key
            newstring += yamlstring[i:valb]
            if yamlstring[valb] == '"' or yamlstring[valb] == "'":
                #value ends at next " or '
                vale = findNextChar(yamlstring, valb+1, yamlstring[valb])
            else:
                #value ends before next whitespace
                vale = findNextWhitespace(yamlstring,valb)
            if(key in suiteparams):
                val = suiteparams[key]
                del suiteparams[key]
            else:
                val = yamlstring[valb:vale]
            newstring += str(val)
            i = vale
        newstring+=yamlstring[i:]
        return newstring

    def loadTestsFromTestCase(self, testCaseClass, params={}, testargs={}):
        """Return a suite of all tests cases contained in testCaseClass"""

        if issubclass(testCaseClass, unittest.TestSuite):
            raise TypeError("Test cases should not be derived from TestSuite."
                            " Maybe you meant to derive from TestCase?")
        testCaseNames = self.getTestCaseNames(testCaseClass)
        if not testCaseNames and hasattr(testCaseClass, 'runTest'):
            testCaseNames = ['runTest']
        if 'id' in testargs:
             testname=testargs['id']
        else:
             testname=".".join([testCaseClass.__module__,testCaseClass.__name__])
        loaded_suite = self.suiteClass([
                testCaseClass(name, **params) for name in testCaseNames],
                   testname)
        return loaded_suite

    def loadTestsFromModule(self, module, use_load_tests=True, params={}, testargs={}):
        """Return a suite of all tests cases contained in the given module"""
        tests = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                tests.append(self.loadTestsFromTestCase(obj, params=params, testargs=testargs))

        load_tests = getattr(module, 'load_tests', None)
        tests = self.suiteClass(tests, module)
        if use_load_tests and load_tests is not None:
            if params:
                raise TypeError(
                    "cannot load parametrized tests with load_tests method:"
                    " %s"%(module))
            try:
                return load_tests(self, tests, None)
            except Exception, e:
                return _make_failed_load_tests(module.__name__, e,
                                               self.suiteClass)
        tests.testargs = testargs
        return tests

    def loadTestsInSuite(self, tests, testargs={}, testtype=None):
        """Process tests given as argument.
           Input:
             tests: a list of tests coming from a suite yaml
             testargs: testargs from parent suite
             testtype: an attribute to put in testargs
           Output:
             a list of tests
        """
        testlist = []

        if tests is None:
            raise Exception('\n\nFailed to load test suites\nIt is not allowed to have an empty setup/test or teardown sections!\n')

        for test in tests:
            test = test.items()
            assert len(test) == 1
            (test_name, attr) = test[0]

            # If any testargs are to be inherited from 'mother' suite do it here
            subtestargs = {}

            if 'exit-on-error' in testargs:
                subtestargs['exit-on-error'] = testargs['exit-on-error']

            # Running a 'setup' test implicitely means exit on error
            # for children
            if 'setup' in testargs:
                subtestargs['exit-on-error'] = True

            if testtype:
                subtestargs[testtype] = True

            if test_name.startswith("."):
                test_name = ".".join(parts[1:-1] + [test_name[1:]])
            try:
                if attr and attr.has_key('params'):
                    params = attr['params']
                else:
                    params = {}

                # All other arguments are meant to be test-args somehow used by the
                # framework
                tmp_args = {}
                if attr:
                    tmp_args.update(attr)
                    if tmp_args.has_key('params'):
                        del tmp_args['params']

                subtestargs.update(tmp_args)

                # Validate test args on load
                self.validateTestArgs(subtestargs)

                test = self.loadTestsFromName(test_name, params=params,testargs=subtestargs)
                test.testargs = subtestargs
            except:
                logging.error('failed to load test: %s'%(test_name))
                raise
            if test is None:
                logging.error('failed to load test: %s'%(test_name))
                raise Exception()
            def boolean_attr(attr_name):
                return attr and attr_name in attr and bool(attr[attr_name])
            if boolean_attr('expected_failure'):
                for test in test._tests:
                    assert not hasattr(test, '_testMethod')
                    testMethodName = getattr(test, '_testMethodName')
                    setattr(test, '_testMethod', getattr(test, testMethodName))
                    setattr(test, testMethodName, unittest.expectedFailure(
                            test._testMethod))

            # We accept empty sub-test-suites
            if not len(test._tests) is 0:
                testlist.append(test)

        return testlist

    def loadTestSuiteFromSpecification(self, name, path, testargs={}, suiteparams={}):
        """Return a suite from specification file"""

        if 'id' in testargs:
            dir_name = testargs['id']
        else:
            dir_name = name

        name = name.split('.')
        parts = [path] + name
        filename = os.path.join(*parts) + '.yaml'
        if not os.path.exists(filename):
            parts.append('all')
            filename = os.path.join(*parts) + '.yaml'
            if not os.path.exists(filename):
                return None
        self.logger.debug(
            "loading test suite YAML specification: %s"%(filename))

        try:
            with open(filename, 'r') as f:
                #parameters sent into this suite
                #override the loaded suite yaml
                if(suiteparams):
                    assert isinstance(suiteparams,dict),"suite params must be a dict"
                    yamlstring = f.read()
                    updatedyaml = self.updateSuiteParams(yamlstring,suiteparams)
                    #check if a param to the suite was not used, warn
                    for k in suiteparams:
                        print "WARNING: specified suite param not used: ",k
                    spec = yaml.load(updatedyaml)
                else:
                    spec = yaml.load(f)
        except yaml.composer.ComposerError,e:
            print "ERROR: "+str(e)
            print "Did you forget to set default suite parameters?"
            return

        if 'testargs' in spec:
            local_testargs = spec['testargs']
            try:
                for arg in local_testargs:
                   for key in arg.keys():
                      if not key in testargs:
                          testargs[key] = arg[key]
            except:
                print ""
                print "WARNING testargs in suite %s not properly defined. "%(filename)
                print "Must be a list of dicts. Setting ignored"
                print ""

        tests = []
        if not 'description' in spec:
            # No description given - create a default on - the name of the suite relative to
            # the cur directory.
            # TODO: Suite must always have decriptions - to generate meaningful reports!?
            spec['description'] = "Test suite (%s)"%os.path.relpath(filename)

        if not 'tests' in spec:
            self.logger.debug('empty test suite specification: %s'%(filename))
            return self.suiteClass(tests, filename)

        if 'setup' in spec:
            testlist = self.loadTestsInSuite(spec['setup'], testargs, 'setup')
            for test in testlist:
                tests.append(test)

        if 'tests' in spec:
            testlist = self.loadTestsInSuite(spec['tests'], testargs)
            for test in testlist:
                tests.append(test)
        else:
            print 'WARNING: no tests in suite %s'%(name)

        if 'teardown' in spec:
            testlist = self.loadTestsInSuite(spec['teardown'], testargs, 'teardown')
            for test in testlist:
                tests.append(test)

        suite = self.suiteClass(tests, dir_name)
        suite.testargs = testargs
        suite.__doc__ = spec['description']
        return suite

    def _loadTestsFromName(self, path, name, module=None, params={}, testargs={},
                           use_load_test=True):
        """Return a suite of all test cases given a string specifier.

        The name may resolve either to a test suite specification (YAML
        format), a module, a test case class, a test method within a test case
        class, a callable object which returns a TestCase or TestSuite
        instance, or may be produced by a test case factory.

        A test case factory is a module defining a 'load_test' method, which
        should produce a single TestCase instance or None.  The load_test
        method will be called with the remaining name parts and optionally
        parameters, as load_test(parts, param=None).

        The method optionally resolves the names relative to a given module.

        This method is an extended version of the TestLoader.loadTestsFromName
        from unittest.
        """

        self.logger.debug('_loadTestsFromName %s', name)
        self.logger.debug('sys.path %s', sys.path)

        #NOTE: Because of yaml anchor/ref syntax it is currently needed to
        #      explicitly set a suite-param to "null" which will pass in
        #      the argument as None. We remove these params here, since it
        #      means the same as not have that argument specified and to
        #      avoid rewriting the test-case code. E.g. for dctrl an arg
        #      explicitly set to None would override a default value
        for k in copy.copy(params):
            if(params[k] is None):
                del params[k]

        suite = self.loadTestSuiteFromSpecification(name, path, testargs=testargs, suiteparams=params)
        if suite:
            self.logger.debug("loaded test suite from specification: %s"%(name))
            self.logger.debug("Description in test suite says: '%s'"%(suite.__doc__))
            return suite

        all_parts = parts = name.split('.')
        if module is None:
            parts_copy = parts[:]
            while parts_copy:
                try:
                    self.logger.debug("trying to import: "+str('.'.join(parts_copy)))
                    module = __import__('.'.join(parts_copy), level=0)
                    break
                except ImportError:
                    del parts_copy[-1]
                    if not parts_copy:
                        return None
            parts = parts[1:]
        obj = module
        try:
            for i in range(len(parts)):
                parent, obj = obj, getattr(obj, parts[i])
        except AttributeError, e:
            m = re.search("has no attribute '(.*)'", e.args[0])
            if not m or not m.group(1) in parts:
                raise
            load_test = getattr(obj, 'load_test', None)
            if use_load_test and load_test is not None:
                sname = '.'.join(parts[i:])
                pname = '.'.join(all_parts[:i+1])
                test = load_test(pname, sname, params, testargs=testargs)
                if test is None:
                    raise TypeError(
                        "cannot load test from load_test factory: %s"%(sname))
                if test:
                    if 'id' in testargs:
                        testname = testargs['id']
                    else:
                        testname = name
                    test.testargs = testargs
                    # Store the parameters which are explicit given as input parameters
                    # This enable the parameters to be used later
                    test.inputparams = params
                    return self.suiteClass([test], testname)
            return None
        except ImportError, e:
            if e.args[0] != 'No module named %s'%(path[0]):
                raise
            return None

        if isinstance(obj, types.ModuleType):
            return self.loadTestsFromModule(obj, params=params,testargs=testargs)
        elif isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            # TODO: we might need to create dirs for each test_ method
            #       but unique naming is a challenge, for now the leaf
            #       of the dir tree is TestCase classes
            if 'id' in testargs:
                testname = testargs['id']
            else:
                testname = name
            return self.loadTestsFromTestCase(obj, params, testargs=testargs)
        elif (isinstance(obj, types.UnboundMethodType) and
              isinstance(parent, type) and
              issubclass(parent, unittest.TestCase)):
            if 'id' in testargs:
                testname = testargs['id']
            else:
                testname = name
            return self.suiteClass([parent(obj.__name__, **params)], testname)
        elif hasattr(obj, '__call__'):
            test = obj(**args)
            if isinstance(test, unittest.TestSuite):
                return test
            elif isinstance(test, unittest.TestCase):
                return self.suiteClass([test], test.__class__.__name__)
            else:
                raise TypeError("calling %s returned %s, not a test" %
                                (obj, test))
        else:
            raise TypeError("don't know how to make test from: %s" % obj)

    def loadTestsFromName(self, name, module=None, params={}, testargs={}):
        if module:
            return self._loadTestsFromName(self.path[0], name, module, params=params, testargs=testargs)
        #sys_path = sys.path
        #for path in self.path:
            #sys.path = [path] + sys_path
        for layer in self.overlays + ['']:
                layer = filter(len, layer.split('.'))
                self.logger.debug('layer: %s', layer)
                self.logger.debug('name: %s', name)
                assert not name.startswith('/')
                overlayed_name = '.'.join(layer + name.split('.'))
                self.logger.debug('overlayed_name: %s', overlayed_name)
                for path in self.path:
                    tests = self._loadTestsFromName(path, overlayed_name, params=params, testargs=testargs)
                    if tests is not None:
                        self.logger.debug('loaded tests: %s'%(overlayed_name))
                        #sys.path = sys_path
                        return tests
        #sys.path = sys_path
        raise TypeError("unable to load test: %s"%(name))
