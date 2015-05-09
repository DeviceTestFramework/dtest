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

import logging
import unittest
import random
from dtest.dtestcase import DtestTestCase
import os
import yaml


logger = logging.getLogger("selftest")

class BooleanTestCase(DtestTestCase):

    def test_pass(self):
        """Test case that must pass."""
        pass

    @unittest.expectedFailure
    def test_fail(self):
        """Test case that must fail."""
        self.fail('failing on purpose')

    @unittest.skip('always')
    def test_skip(self):
        """Test case that must be skipped."""
        self.fail('should have been skipped')

    def test_real_fail(self):
        """Test case resulting in real fail."""
        self.fail('Failing on purpose')


    def test_random_result(self):
        """
        Test case resulting in either a real fail/pass.
        It can be used for testing purposes.
        """
        number = random.randint(1, 10)
        if number > 5:
            self.fail('Failing on purpose %s'%(number))
        pass


class OutputStructure(DtestTestCase):
    def __init__(self, methodName='runTest', expected_content = [], mode='result'):
        """
        Test that the folder structure of the correct.
        mode determines which folder structure is checked: either 'result' or 'tmp'
        """
        self.expected_content = expected_content
        self.mode = mode
        super(OutputStructure, self).__init__(methodName)

    def runTest(self):
        """
        Test the structure of either the tmp or result folder
        According to self.mode either the resultDir or the tmpDir will be checked
        """

        # The path to the suite which we are currently in
        # All folders will be check according to this folder
        if self.mode == 'result':
            self.suite_path = os.path.join(self.resultDir, '../')
        else:
            # tmp mode
            self.suite_path = os.path.join(self.tmpDir, '../')

        for expected_path in self.expected_content:
            folder = os.path.join(self.suite_path,expected_path)
            self.assertTrue(os.path.exists(folder), msg="folder %s does not exist as expected"%(folder))
        pass

class DescriptionDocString(DtestTestCase):
    """
    Class used to test if the correct description ends up in the result files.
    """
    def __init__(self, methodName='runTest'):
        super(DescriptionDocString, self).__init__(methodName)

    def runTest(self):
        """This is the docstring of the class: DescriptionFull (runtest)"""
        pass

class DescriptionShortDescription(DescriptionDocString):
    def __init__(self, methodName='runTest'):
        super(DescriptionShortDescription, self).__init__(methodName)

    def shortDescription(self):
        return "I'm the short description of DescriptionShortDescription"


class DescriptionFullDescription(DescriptionShortDescription):
    def __init__(self, methodName='runTest'):
        super(DescriptionFullDescription, self).__init__(methodName)

    def fullDescription(self):
        return "I'm the full description of DescriptionFullDescription"


class OutputResultContent(DtestTestCase):
    def __init__(self, methodName='runTest', result_path=None, expected_content=None):
        """
        Test that the result file in the result_path has the particular content as specified in
        expected_content. The expected_content should be given as a dict
        e.g.
        - selftest.OutputResultContent: { params: { result_path: 'DescriptionDocString', expected_content: {description: "This is the docstring of the class: DescriptionFull (runtest)" } }}

        """
        self.expected_content = expected_content
        self.result_path = result_path
        self.assertIsNotNone(self.expected_content, "expected_content parameter should be given!")
        self.assertIsNotNone(self.result_path, "result_path parameter should be given!")
        super(OutputResultContent, self).__init__(methodName)

    def runTest(self):
        # Check that the file exists at all
        self.suite_path = os.path.join(self.resultDir, '../')
        result_file = os.path.join(self.suite_path,self.result_path,'result.yaml')
        self.assertTrue(os.path.exists(result_file), msg="folder %s does not exist as expected"%(result_file))

        logger.info("loading: %s"%(result_file))
        resDict = yaml.load(file(result_file,'r'))

        for key in self.expected_content:
            if key in resDict:
                # Found the matching key - check if the content is matching too
                if resDict[key] != self.expected_content[key]:
                    self.fail("The content of key: '%s' did not match\n##### expected: #####\n'%s'\n###### actual:  #####\n'%s'\n"%(key,self.expected_content[key],resDict[key]))
            else:
                self.fail('Missing key: %s in the result.yaml '%(key))
        pass
