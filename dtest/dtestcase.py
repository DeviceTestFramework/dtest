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

class DtestTestCase(unittest.TestCase):
    """
    This is the class to use when writing testcases supposed to run
    in dtest environment.
    This class enriches the unittest.TestCase with a tmpDir attribute

    In case a testcase has to store data to be read by other testcase
    or for e.g. logging, it ought happen in the dir specified by tmpDir.

    The directory is guaranteed to be created before run() is called
    and it is guaranteed not to be given to other testcases.

    The class is futher enriched with resultDir attribute.
    The resultDir is stored to be able use it for selftesting of the
    result-directory layout
    """

    tmpDir = ""
    resultDir = ""

    def fullDescription(self):
        if hasattr(self,'runTest'):
            return self.runTest.__doc__
        else:
            return self.__doc__

    def run(self, result=None, tmpDir=None, resultDir=None):
        self.tmpDir = tmpDir
        self.resultDir = resultDir
        super(DtestTestCase, self).run(result)
