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
import logging
import datetime
import pickle
import fnmatch
import yaml
from dtest.dtestcase import DtestTestCase

logger = logging.getLogger("dtest")

TIMER_FILE = "timerStatus"

class TimerStartTest(DtestTestCase):
    """
    Basically TimerStartTest just provides a test case able to place a
    timestamp in a file in its tmpdir.
    """

    @classmethod
    def setUpClass(cls):
        #print "class setup code here"
        return

    def runTest(self):
        start_time = datetime.datetime.now()
        pickle.dump(start_time, file(os.path.join(self.tmpDir,TIMER_FILE),'w'))

class TimerStopTest(DtestTestCase):
    """
    TimerStopTest is the counterpart to TimerStartTest. Based on a
    TimerStartTest within the same suite it can:
       - report elapsed time back as a metric
       - FAIL if elapsed time too long ( > max_time)
       - FAIL if elapsed time too short ( < min_time)

    Following configuration parameters are supported:
       - min_time (in millisec)
       - max_time (in millisec)
       - start_timer_id
       - metric : override "Time" metric in the result.yaml

    start_timer_id is a parameter to be set if the TimerStartTest being related
    to was assigned an id. In this assign the same value to start_timer_id

    Notice that it is valid to have more TimerStopTest's referring the
    same TimerStartTest
    """


    def __init__(self, name,start_timer_id=None, min_time=None, max_time=None,
                 metric=None):
        self.start_timer_id = start_timer_id
        self.min_time = min_time
        self.max_time = max_time
        self.metric = metric
        super(TimerStopTest, self).__init__(name)

    @classmethod
    def setUpClass(cls):
        #print "class setup code here"
        return

    def runTest(self):
        stop_time = datetime.datetime.now()

        # NOTICE: For now Start and Stop timer must exist on same suite level
        if self.start_timer_id:
            timerDir = os.path.join(os.path.dirname(self.tmpDir),
                                    self.start_timer_id)
        else:
            timerDir = self.tmpDir.replace('TimerStopTest','TimerStartTest')

        timerFile = os.path.join(timerDir, TIMER_FILE)
        self.assertTrue(os.path.exists(timerFile),
                        "Timer file not found" + timerFile)
        start_time = pickle.load(file(timerFile,'r'))
        self.assertIsInstance(start_time,datetime.datetime, "Error: did not load a datetime object")
        time = stop_time - start_time
        output = {}
        if(self.metric):
            output['metric'] = str(self.metric)
        else:
            output['metric'] = "Time"
        output['value'] = time.total_seconds()
        output['unit'] = "s"
        self.output = output
        if self.min_time:
             self.assertTrue(self.min_time < time.total_seconds()*1000, "Duration shorter than " + str(self.min_time) + "ms")
        if self.max_time:
             self.assertTrue(self.max_time > time.total_seconds()*1000, "Duration exceeded " + str(self.max_time) + "ms")

