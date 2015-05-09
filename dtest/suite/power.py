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
import subprocess
from dtest.dtestcase import DtestTestCase
import dtest.testsetup
import os
import time

class PowerControl(DtestTestCase):
    """
    Test class for powering on and off a target. Can be configured
    in dtest.cfg using one or more of the following entries
    PowerControl:
        poweron: ./path/to/power_on/script
        poweroff: ./path/to/power_off/script
        power_cycle_delay: time-in-seconds

    If the configuration is not found it will fall back to manual poweron/off
    A called script must return 0 to make the test pass
    """

    def __init__(self, methodname):
        self.powercycledelay = 10
        # Ought maybe be common in DtestTestCase
        self.testsetup = dtest.testsetup.testsetup();
        if hasattr(self.testsetup, 'PowerControl'):
            config = self.testsetup.PowerControl;
            if 'poweron' in config:
                self.poweron = os.path.abspath(config['poweron'])
            if 'poweroff' in config:
                self.poweroff = os.path.abspath(config['poweroff'])
            if 'power_cycle_delay' in config:
                self.powercycledelay = config['power_cycle_delay']

        super(PowerControl, self).__init__(methodname)

    def power_on(self):
        """Power on target board."""
        if hasattr(self, 'poweron'):
            self.assertTrue(os.path.isfile(self.poweron))
            retcode = subprocess.call(self.poweron)
            self.assertEqual(retcode, 0)
            return

        raw_input("\nPower on board and press <ENTER>")
        return

    def power_off(self):
        """Power off target board."""
        if hasattr(self, 'poweroff'):
            self.assertTrue(os.path.isfile(self.poweroff))
            retcode = subprocess.call(self.poweroff)
            self.assertEqual(retcode, 0)
            return

        raw_input("\nPower off board and press <ENTER>")
        return

    def power_cycle(self):
        """Power cycle target board."""
        self.power_off()
        time.sleep(int(self.powercycledelay))
        self.power_on()
