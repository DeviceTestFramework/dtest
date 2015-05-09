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
import time
import logging
import subprocess
import os
from dtest.dtestcase import DtestTestCase
import platform
import dtest.testsetup

class sleep(DtestTestCase):

    def __init__(self, methodName='runTest', s=0, ms=0, us=0):
        self.seconds = s + ms / 1000 + us / 1000000
        logging.debug('sleep seconds is %.3f'%(self.seconds))
        super(sleep, self).__init__(methodName)

    def fullDescription(self):
        return self.shortDescription()

    def shortDescription(self):
        return 'Wait for %.3f seconds'%(self.seconds)

    def runTest(self):
        """Sleep a while."""
        time.sleep(self.seconds)

class platform_information(DtestTestCase):
    """
    Use the class to gain information about the SDK host
    The test itself is a dummy - the real information is given in the shor description
    """
    def __init__(self, methodName='runTest'):
        super(platform_information, self).__init__(methodName)

    def fullDescription(self):
        return self.shortDescription()

    def shortDescription(self):
        return 'Host machine: %s (%s)'%(platform.platform(),platform.machine())

    def runTest(self):
        # Dummy - real information is in the description
        pass

class generateDupdateFiles(DtestTestCase):
    """
    This class calls a shell script which generate invalid dupdate packages for a test
    """

    def __init__(self, methodName='runTest', path="suite/pil-basic/dupdate-failures", command="./create_testvectors.sh", args=""):
        self.path = path
        self.command = command
        self.args = args

        # Fetch the name of the machine for from the config file
        try:
            self.testsetup = dtest.testsetup.testsetup();
            config = self.testsetup.Variables;
            self.machine = config['MACHINE']
        except:
            logging.error('Unable to get the required MACHINE variable from the test setup!')
            self.fail(msg='Unable to get the required MACHINE variable from the test setup!')

        super(generateDupdateFiles, self).__init__(methodName)

    def fullDescription(self):
        return self.shortDescription()

    def shortDescription(self):
        return 'Generate dupdate test vectors for machine:\n%s'%(self.machine)

    def runTest(self):
        """Execute command ."""

        # Check if path exists
        self.assertTrue(os.path.isdir(self.path))

        exe_dir = os.getcwd() +"/" +  self.path
        logging.info("Execute command in " + str(exe_dir))

        process = subprocess.Popen([self.command, '-b', self.machine,self.args],cwd=exe_dir,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # wait for the process to terminate
        out, err = process.communicate()
        logging.info("Stdout: " + out)
        logging.info("Stderr:\n" + err)

        errcode = process.returncode
        logging.info("Return code is: " +   str(errcode))
        self.assertEqual(errcode,0,msg="Script returned " + str(errcode))
