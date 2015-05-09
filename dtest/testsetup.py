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

import os
import logging
import yaml

logger = logging.getLogger("dtest")
_singleton = None

def load(filename):
    global _singleton
    config_file = None
    for dirname in ('', 'conf'):
        path = os.path.join(dirname, filename)
        logging.debug("trying to open config file: %s", path)
        if os.path.isfile(path):
            config_file = path
            break
    if not config_file:
        logging.error("cannot find dtest configuration file")
        return
    logging.debug("loading configuration file: %s"%(config_file))
    with open(path, "r") as file:
        d = yaml.load(file)
        d = env_override(d)
        class Namespace(object):
            def __init__(self, adict):
                self.__dict__.update(adict)
        d.setdefault('overlays', [])
        d = { key.replace('-', '_'): val for key, val in d.items() }
        _singleton = Namespace(d)
    return _singleton

def testsetup():
    return _singleton

def env_override(config, env_keys={}, parents=list()):
    """
    searches for yaml entries beginning with 'env-<match>' and overrides
    the value of <match> variables with the value loaded from the environment.

    config: the config to search and override
    env_keys: the <match> part of found entries beginning with 'env-'
    parents: current level of given config (used for printing overridings)
    """
    # look for env-vars at this level
    for key in config:
        if not key.startswith("env"):
            continue

        env_keys[key[4:]] = config[key]

    # for each entry at this level
    for key,val in config.items():
        # recurse into lower level while keeping existing env-vars
        if isinstance(val, dict):
            config[key] = env_override(val, env_keys, parents + [key])

        # replace vars with existing env-vars
        if key in env_keys and env_keys[key] in os.environ:
            logger.debug("replace {}.{} with {}".format(".".join(parents), key, env_keys[key]))
            config[key] = os.environ[env_keys[key]]

    # return modified config to higher levels
    return config
