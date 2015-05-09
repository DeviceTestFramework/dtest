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
import os
import time
import yaml
import logging

logger = logging.getLogger("dtestSuite")

def logSuiteHeader(test):
    if 'name' in test.testargs:
        name = test.testargs['name']
    else:
        name = test.dirname

    print ('*********************************************************')
    print ('** %s'%name)
    print ('*********************************************************')

def _issuite(test):
    return not unittest.suite._isnotsuite(test)

def make_count_result_file(res_dir, name, passed):
    resDict = {}
    resDict['type'] = 'count_or_retry'
    resDict['name'] = name
    resDict['start_time'] = time.time()
    if passed:
        resDict['result'] = 'PASS'
    else:
        resDict['result'] = 'FAIL'

    try:
        with open(os.path.join(res_dir, 'result.yaml'), 'w') as f:
            yaml.dump(resDict, f, explicit_start=True)
    except:
        print 'Error writing count result yaml: %s'%res_dir

class ErrorExitException(Exception):
    def __init__(self,value=""):
        self.value = value;
    def __str__(self):
        return repr(self.value)

class DtestTestSuite(unittest.TestSuite):
    """
    The DtestTestSuite overrides the parents recursive suite handling
    such that the tmpDir attribute in DtestTestCase is handled properly.

    The run() method thus takes care of creating the unique tmpDir before
    executing a testcase (or a nested testsuite)

    DtestTestSuite further more ensures a unique result dir is created for
    each test case. This dir is saved into the result object (ResultClass)
    such that results are saved in a unique directory for each test case
    """

    curdir = ""
    tmp_root = ""
    result_root = ""

    class TestResult:
        """Class to subclass test result types from"""
        result_text = "illegal - do subclass"

    class TestResultPass(TestResult):
        result_text = 'PASS'

    class TestResultFail(TestResult):
        result_text = 'FAIL'

    class TestResultSkip(TestResult):
        result_text = 'SKIP'

    def __init__(self, tests=(), dirname=""):
        self.dirname = dirname
        self.testargs = []
        super(DtestTestSuite, self).__init__(tests)


    def suiteRun(self, result, tmpDir, debug=False):
        """Execute all sub-steps in a test. Returns TRUE if no errors
           Raises exception if error and exit-on-error is set
        """
        test_error = len(result.errors)
        test_failures = len(result.failures)
        errorExit = False
        errorFree = True

        if 'header' in self.testargs:
            logSuiteHeader(self)

        for test in self:
            if result.shouldStop:
                break

            if errorExit:
                # proceed to teardown steps
                if not 'teardown' in test.testargs or not test.testargs['teardown'] is True:
                    continue

            # Up front catch of invalid settings
            if 'exit-on-error' in self.testargs:
                if not self.testargs['exit-on-error']:
                    raise AttributeError('Only valid value of exit-on-error is true')

            if unittest.suite._isnotsuite(test):
                self._tearDownPreviousClass(test, result)
                self._handleModuleFixture(test, result)
                self._handleClassSetUp(test, result)
                result._previousTestClass = test.__class__

                if (getattr(test.__class__, '_classSetupFailed', False) or
                    getattr(result, '_moduleSetUpFailed', False)):
                    continue

            if 'header' in self.testargs:
                if not 'header' in test.testargs:
                    logSuiteHeader(test)


            if not debug:
                res = test(result, tmpDir=tmpDir,resultDir=result.result_dir)
            else:
                res = test.debug()

            test_failed = False

            if isinstance(test, DtestTestSuite):
               if isinstance(res.passed,self.TestResultFail):
                    test_failed = True
            else:
               if (len(result.errors) + len(result.failures) ) - (test_error + test_failures) != 0:
                    test_failed = True

            if test_failed:
                errorFree = False

                # Check for configured exit on error
                if 'exit-on-error' in self.testargs:
                    errorExit=True
                # Automatic exit-on-error if error in setup tests
                if hasattr(self,'testargs'):
                    if 'setup' in self.testargs and self.testargs['setup'] is True:
                        errorExit=True
                if hasattr(test,'testargs'):
                    if 'setup' in test.testargs and test.testargs['setup'] is True:
                        errorExit=True

        # Now that all teardowns have been processed we can raise execption
        if errorExit:
             raise ErrorExitException()

        return errorFree

    # This method is a complete override of TestSuite.run
    def run(self, result, debug=False, resultDir=None, tmpDir=None):
        topLevel = False
        if getattr(result, '_testRunEntered', False) is False:
            result._testRunEntered = topLevel = True
            logger.debug("Setting result_root as %s"%(resultDir))
            DtestTestSuite.result_root = resultDir
            DtestTestSuite.tmp_root = tmpDir

        path = DtestTestSuite.curdir

        # Exstract the count variable - used to repeat a test
        if 'count' in self.testargs:
            count=self.testargs['count']
        else:
            count=1

        # Extract the retry variable - used to repeat a test until success
        if 'retry' in self.testargs:
            retry=self.testargs['retry']
        else:
            retry=1

        logger.debug("Result dir input is: %s"%(resultDir))
        logger.debug("Tmp dir input is: %s"%(tmpDir))

        # allow the same test case to be run multiple times in one suite
        # Generate unique dir name - based if the result dir already exists
        # Afterwards modify the curdir to match that new directory
        # NOTE: The curdir may be altered again further down in case the
        # test has to be repeated (count > 1)

        # Base the new directory name on the test name
        new_dir = self.dirname
        # Default is to place the directory in the root + the current path + new_dir
        new_abs_result_path=os.path.join(DtestTestSuite.result_root,path,new_dir)
        i=0
        while(os.path.exists(new_abs_result_path)):
            # Append a number and retry
            i+=1
            logger.debug("new_abs_result_path already existed %s"%(new_abs_result_path))
            new_dir = self.dirname+"-"+str(i)
            new_abs_result_path=os.path.join(DtestTestSuite.result_root,path, new_dir)

        DtestTestSuite.curdir = os.path.join(path, new_dir)
        logger.debug("Setting DtestTestSuite.curdir to %s"%(DtestTestSuite.curdir))

        result.result_dir= os.path.join(DtestTestSuite.result_root, DtestTestSuite.curdir)
        tmpDir = os.path.join(DtestTestSuite.tmp_root, DtestTestSuite.curdir)

        # When coming here result_dir is unique.
        base_result_dir = result.result_dir
        base_tmp_dir = tmpDir

        logger.debug("Result dir is: %s"%(result.result_dir))
        logger.debug("base_tmp_dir is: %s"%(base_tmp_dir))


        pre_errors = len(result.errors)
        pre_failures = len(result.failures)
        pre_runs = result.testsRun

        final_result = self.TestResultPass()
        retry_attempts = 0

	# Use count to iterate
        if retry > 1:
            count = retry
            if not hasattr(result,'retries'):
                result.retries = 0

        # Store the start time of the test suite
        start_time=time.time()

        try:
            # backup the curdir.
            # "DtestTestSuite.curdir" is modified if the test uses "count"
            org_curdir =  DtestTestSuite.curdir
            for i in xrange(0,count):
                logger.debug("Loop number %s"%(i))

                if count == 1:
                    # don't make separate dirs
                    extra_dirname = ""
                else:
                    extra_dirname = os.sep + "run-%d"%(i+1)

                result.result_dir = base_result_dir + extra_dirname
                tmpDir = base_tmp_dir + extra_dirname
                DtestTestSuite.curdir  = org_curdir + extra_dirname

                os.makedirs(result.result_dir)
                os.makedirs(tmpDir)

                try:
                    pre_runcnt = result.testsRun
                    retry_attempts +=1
                    res = self.suiteRun(result, tmpDir, debug)

                    if count > 1:
                        res_dir = base_result_dir + extra_dirname
                        make_count_result_file(res_dir, extra_dirname, res)

                    if not res:
                        final_result = self.TestResultFail()
                    if retry > 1:
                        if res:
                            # No further retries - proceed to next test
                            # Remove errors and reset runs accumulated during
                            # our failed attempts
                            del result.errors[pre_errors:]
                            del result.failures[pre_failures:]
                            post_runcnt = result.testsRun
                            result.testsRun = pre_runs + (post_runcnt - pre_runcnt)

                            final_result = self.TestResultPass()
                            break;
                        else:
                            result.retries += 1
                            if i < retry-1:
                                print '************** RETRYING ***************'
                            else:
                                print '*********** MAX RETRIES REACHED *******'
                except ErrorExitException:
                    if retry == 1 or i+1 == count:
                        raise ErrorExitException()

        except ErrorExitException:
            final_result = self.TestResultFail()
            print 'Testsuite %s aborted'%(self.dirname)

        self.updateResultFile(base_result_dir, final_result, start_time, retry, retry_attempts)

        logger.debug("Setting curdir back to path: %s"%(path))
        DtestTestSuite.curdir = path
        if topLevel:
            self._tearDownPreviousClass(None, result)
            self._handleModuleTearDown(result)
            result._testRunEntered = False
        result.passed = final_result
        return result


    def updateResultFile(self, res_dir, final_result, start_time, retry_max=0, count=1):
        if os.path.exists(os.path.join(res_dir, 'result.yaml')):
            resDict = yaml.load(file(os.path.join(res_dir, 'result.yaml'),'r'))
        else:
            resDict = {}

        # The start time should be a part of the result
        if not 'start_time' in resDict:
            resDict['start_time'] = start_time

        if 'type' in self.testargs:
            resDict['type'] = self.testargs['type']
        elif 'setup' in self.testargs:
            resDict['type'] = 'setup'
        elif 'teardown' in self.testargs:
            resDict['type'] = 'teardown'

        if not 'type' in resDict:
            resDict['type'] = 'suite'

        # Ensure description always exists in result.
        # Make report generation decide whether to use it or not
        if not 'description' in resDict:
            resDict['description'] = self.__doc__

        if 'name' in self.testargs:
            resDict['name'] = self.testargs['name']
        else:
            resDict['name'] = self.dirname

        if 'flag' in self.testargs:
            resDict['flag'] = self.testargs['flag']

        if not 'result' in resDict:
            resDict['result'] = final_result.result_text

        if 'count' in self.testargs:
            logger.debug("Test has a count argument (%s)"%(self.testargs['count']))
            resDict['count'] = self.testargs['count']

        if 'retry' in self.testargs:
            resDict['retry-max'] = self.testargs['retry']
            resDict['retries'] = count

        try:
            with open(os.path.join(res_dir, 'result.yaml'), 'w') as f:
                yaml.dump(resDict, f, explicit_start=True)
        except:
            print 'Error writing result.yaml for suite'

