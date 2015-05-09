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

import unittest
import logging
import sys
import os
import time
import yaml
import dctrl
import ast

# override TestCase '__str__' method
def dtest_testcase_str(self):
    if hasattr(self, '_testName'):
        test_name = self._testName
    else:
        test_name = self._testMethodName
    return '.'.join((self.__class__.__module__,
                     self.__class__.__name__,
                     self._testMethodName))
unittest.TestCase.__str__ = dtest_testcase_str

class DTestResult(unittest.result.TestResult):
    """The dtest test result class

    Used by DTestRunner.
    """
    separator1 = '=' * 70
    separator2 = '-' * 70

    # result output:
    #   * success: True/False
    #   * result: simple string, no newlines
    #   * log: multi-line string
    #   * errors: multi-line string

    def __init__(self, descriptions=True, show_time=True, store_result=True):
        super(DTestResult, self).__init__()

        self.success = None
        self.result = None
        self.descriptions = descriptions
        self.show_time = show_time
        self.store_result = store_result
        if sys.platform.lower().startswith('linux'):
            rows, columns = os.popen('stty size', 'r').read().split()
        else:
            import struct
            from ctypes import windll, create_string_buffer
            # stdin handle is -10
            # stdout handle is -11
            # stderr handle is -12
            h = windll.kernel32.GetStdHandle(-12)
            csbi = create_string_buffer(22)
            res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
            if res:
                (bufx, bufy, curx, cury, wattr,
                 left, top, right, bottom,
                 maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
                columns = right - left + 1
                rows = bottom - top + 1
            else:
                columns = 160 #running headless
        self.columns = int(columns)
	if self.columns == 0:
	   self.columns = 160

    def wasSuccessful(self):
        "Tells whether or not this result was a success"
        return len(self.failures) == len(self.errors) == len(self.unexpectedSuccesses) == 0


    def getDescription(self, test):
        description = test.shortDescription()
        if self.descriptions and description:
            return '%s %s'%(str(test), description)
        else:
            return str(test)

    def startTest(self, test):
        super(DTestResult, self).startTest(test)
        self.log = ""
        self.err = ""
        self.start_time = time.time()
        line = self.getDescription(test)

        line_length = int(line.__len__())

        # Text should end 20 char from right-handside of the terminal
        # It makes space for the verdict
        max_length = self.columns -20
        line_start=0

        allow_multiline = True

        if allow_multiline:
            number_of_lines = line_length // max_length
            for line_number in range(0,number_of_lines):
                print "%s"%line[line_start:line_start+max_length]
                line_start=line_start+max_length

        # Python seems to not care about indexing outside the string..
        nline = line[line_start:line_start+max_length]
        print "%s "%(nline.ljust(max_length,'.')),
        # Flush the content of the line so fare - in order to see the current test running
        sys.stdout.flush()

    def addResult(self, test, result):
        if self.show_time and hasattr(self, 'start_time'):
            time_spent = time.time() - self.start_time
            print '%s [%.3fs]'%(result, time_spent)
        else:
            print result

        if self.store_result:
            resDict = {}
            resDict['result'] = result
            resDict['time'] = time_spent
            # Store start time for report generation
            resDict['start_time'] = self.start_time
            resDict['type'] = 'teststep'
            # Store the description for report generation
            resDict['description'] = '%s'%test.fullDescription()

            if hasattr(test,'params'):
                # Test case has parameters - store them

                # Delete the run entry - it is causing issues when loading the result.yaml again
                # in dtestSuite
                import copy
                # Make a deep copy - to be sure not to mess with the current object
                tmpparams =   copy.deepcopy(test.params)
                del tmpparams['run']
                resDict['params'] = tmpparams

            if hasattr(test,'inputparams'):
                # Test case had input parameters, i.e. parameters specified in the suite/test
                resDict['inputparams'] = test.inputparams

            if hasattr(test,'testargs') and 'name' in test.testargs:
                resDict['name'] = test.testargs['name']
            elif (hasattr(dctrl,"unittest") and
                 isinstance(test,dctrl.unittest.DctrlWrapper)):
                     resDict['name'] = unittest.util.strclass(test.cmd.__class__)
            else:
                resDict['name'] = unittest.util.strclass(test.__class__)

            if hasattr(test, 'testargs') and 'flag' in test.testargs:
                resDict['flag'] = test.testargs['flag']
                # Don't think this should ever happen
                # and if it does - will flag then be correct?
                # Let's for now raise an exception to see if occurs
                raise Exception("Debug: Please check if flag is intended and as expected")

            if (hasattr(test, "output")):
               try:
                 resDict['output'] = ast.literal_eval(test.output)
               except Exception, e:
                 resDict['output'] = test.output

            path = self.result_dir
            with open(os.path.join(path, 'result.yaml'), 'a') as f:
                yaml.dump(resDict,f, explicit_start=True)
            if hasattr(self, 'log') and self.log:
                with open(os.path.join(path, 'log'), 'w') as f:
                    f.write(self.err)
            if hasattr(self, 'err') and self.err:
                with open(os.path.join(path, 'err'), 'w') as f:
                    f.write(self.err)

    def addSuccess(self, test):
        super(DTestResult, self).addSuccess(test)
        self.addResult(test, 'PASS')

    def addError(self, test, err):
        super(DTestResult, self).addError(test, err)
        self._mirrorOutput = False
        self.addResult(test, 'ERROR')

    def addFailure(self, test, err):
        super(DTestResult, self).addFailure(test, err)
        self._mirrorOutput = False
        self.addResult(test, 'FAIL')

    def addSkip(self, test, reason):
        super(DTestResult, self).addSkip(test, reason)
        reason = "{0!s}".format(reason)
        if reason:
            #self.addResult(test, 'SKIP (%s)'%(reason))
            self.addResult(test, 'SKIP')
        else:
            self.addResult(test, 'SKIP')

    def addExpectedFailure(self, test, err):
        super(DTestResult, self).addExpectedFailure(test, err)
        #self.addResult(test, 'PASS (expected failure)')
        self.addResult(test, 'PASS')

    def addUnexpectedSuccess(self, test):
        super(DTestResult, self).addUnexpectedSuccess(test)
        #self.addResult(test, 'FAIL (unexpected success)')
        self.addResult(test, 'FAIL')

    def printErrors(self):
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            print "%s: %s" % (flavour,self.getDescription(test))
            print "%s" % err.rstrip()
            print


class DTestRunner(object):
    """The dtest test runner class"""

    resultclass = DTestResult

    def __init__(self, descriptions=True, verbosity=2, failfast=False,
                 show_time=True, show_errors=True, show_summary=True,
                 resultclass=None):
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.failfast = failfast
        self.show_time = show_time
        self.show_errors = show_errors
        self.show_summary = show_summary
        if resultclass is not None:
            self.resultclass = resultclass

    def run(self, test, resultDir, tmpDir):
        """Run the given test case or test suite"""

        result = self.resultclass(
                     descriptions=self.descriptions, show_time=self.show_time)

        unittest.signals.registerResult(result)
        result.failfast = self.failfast

        start_time = time.time()
        def result_func(name):
            func = getattr(result, name, None)
            if func is not None:
                func()
        result_func('startTestRun')
        try:
            # redirect logging, stdout, and stderr output to buffer
            test(result=result, resultDir=resultDir, tmpDir=tmpDir)
        finally:
            result_func('stopTestRun')
        time_spent = time.time() - start_time
        print

        count = {}
        count['testsRun'] = successes = result.testsRun
        for vector in ('failures', 'errors', 'skipped',
                       'expectedFailures', 'unexpectedSuccesses'):
            val = len(getattr(result, vector))
            count[vector] = val
            successes -= val
        assert successes >= 0
        count['successes'] = successes
        count['passed'] = count['successes'] + count['expectedFailures']
        count['flunked'] = count['failures'] + count['unexpectedSuccesses']

        if self.show_errors:
            result.printErrors()

        if self.show_summary:

            print 'Ran for %.3f seconds' % time_spent
            print
            print 'Tests cases:            %d' % count['testsRun']
            print 'Passed:                 %d' % count['passed'],
            print '  successes: %d ' % count['successes'],
            print '  failures: %d' % count['expectedFailures']
            #print 'Passed:                 %d' % count['passed']
            #print '  Expected successes:   %d' % count['successes']
            #print '  Expected failures:    %d' % count['expectedFailures']
            print 'Flunked:                %d' % count['flunked'],
            print '  failures: %d ' % count['failures'],
            print '  successes: %d' % count['unexpectedSuccesses']
            #print 'Flunked:                %d' % count['flunked']
            #print '  Unexpected failures:  %d' % count['failures']
            #print '  Unexpected successes: %d' % count['unexpectedSuccesses']
            print 'Errors:                 %d' % count['errors']
            print 'Skipped:                %d' % count['skipped']
            if hasattr(result,'retries'):
                print 'Retries:                %d' % result.retries
            print

        return result
