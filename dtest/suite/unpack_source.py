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
import tarfile
import logging
import os
import subprocess
from dtest.dtestcase import DtestTestCase
import dtest.testsetup
import shutil

logger = logging.getLogger("dtest")

class tar(DtestTestCase):

    def __init__(self, methodName='runTest', path="none", extract_path="",extractRelativeTmp=True):
        """
        Arguments:
        path: path and name of the tar ball. The name should be given relative to the src dir
        extract_path: The path to where the file should be extracted (dir created if it does not exist)
        extractRelativeTmp: If True extracted relative to self.tmpDir else relative to the src dir
        """
        self.testsetup = dtest.testsetup.testsetup()

        # File to extract
        self.filepath = os.path.join(self.testsetup.src_path,path)
        if not (os.path.exists(self.filepath)):
            raise AssertionError("File '" + self.filepath + "' does not exist")

        self.path = path
        self.extract_path = extract_path
        self.extractRelativeTmp = extractRelativeTmp
        super(tar, self).__init__(methodName)

    def runTest(self):
        """Unpack tarfile relative to srcdir"""
        try:
                tarfile.is_tarfile(self.filepath)
                logger.debug("Tarfile Acquired: %s"%self.filepath)
        except IOError, err:
                self.fail("%s is not a tarfile."%self.filepath)
        tar = tarfile.open(self.filepath)

        if self.extractRelativeTmp:
            extractDir = os.path.join(self.tmpDir,self.extract_path)
        else:
            extractDir = os.path.join(self.testsetup.src_path,self.extract_path)
            if self.extract_path:
                # Clean the dir when given and it exists already
                if(os.path.isdir(extractDir)):
                    shutil.rmtree(extractDir)

        if not (os.path.isdir(extractDir)):
            os.makedirs(extractDir)
            logger.debug("Create dir: %s"%(extractDir))

        tar.extractall(path=extractDir)
        tar.close()

	pass
