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
# This file provides handles for post processing the result tree generated
# by a dtest run
#

import yaml
import os
import logging
import glob
from operator import itemgetter, attrgetter # Be able to sort

logger = logging.getLogger("result_parse")

uniq_name_list=[]

class result_node(object):
    root=False
    parent=None
    name=""
    level=0
    result={'result': '----'}
    start_time=None

    def __init__(self, path, name, root=False):
        self.name = name
        self.path = path
        self.children = []
        self.root=root

    def add_child(self, child):
        self.children.append(child)
        child.parent = self
        child.level = self.level+1

class suite_result(result_node):
    pass

class suite_setup(result_node):
    pass

class suite_teardown(result_node):
    pass

class testcase_result(result_node):
    pass

class teststep_result(testcase_result):
    pass

class count_or_retry(result_node):
    pass

def process_dirs(path, parrent_node):
   result_file = os.path.join(path,"result.yaml")
   if os.path.exists(result_file):
       result = yaml.load(file(result_file,'r'))
       if 'name' in result:
           name=result['name']
       else:
           name=os.path.basename(path)
       if 'type' in result:
           if result['type'] == 'suite':
               node = suite_result(path, name)
           elif result ['type'] == 'testcase':
               node = testcase_result(path, name)
           elif result ['type'] == 'setup':
               node = suite_setup(path, name)
           elif result ['type'] == 'teardown':
               node = suite_teardown(path, name)
           elif result ['type'] == 'count_or_retry':
               node = count_or_retry(path, name)
           else:
               node = teststep_result(path, name)
       else:
          node = teststep_result(path, name)

       if 'start_time' in result:
           node.start_time = result['start_time']
       else:
           # Raise error - potential the timestamp of the file could be used
           logger.error("Error: no starttime in result!")
           raise ValueTypeError()

       logger.debug("Adding child with name %s "%(node.name))
       parrent_node.add_child(node)

       node.result = result
   else:
       # No yaml file ???
       logger.warning("Missing file %s"%(result_file))
       node = parrent_node
       #node = count_or_retry(path)

   # Process dirs in folder
   dirs = filter(os.path.isdir, glob.glob(path + "/*"))
   for subdir in dirs:
       process_dirs(subdir, node)

def generate_node_tree(rootpath, uniq_names=False, keep_multiple_runs=True):
    """
    generate_node_tree is the initial function to call.
    Input:
      rootpath: path, relative or absolute to the directory holding the
                result from a dtest run
      uniq_names: If True then give the names a uniq name by adding a dynamic number
      keep_multiple_runs: If False, all siblings of type count_or_retry but one are removed

    Output:
      a result_node tree
    """

    ch = logging.StreamHandler()
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

    topnode = result_node(rootpath, 'ROOT', True)
    if not os.path.isdir(rootpath):
        logger.error("Error: rootpath not a dir")
        raise ValueTypeError()

    # Parse all dirs unconditional to build node tree
    dirs = filter(os.path.isdir, glob.glob(rootpath))
    for subdir in dirs:
        process_dirs(subdir,topnode)

    # Now sort the node tree according to start time
    sort_results(topnode)

    if not keep_multiple_runs:
        clean_count_or_retry(topnode)

    if uniq_names:
        uniq_name(topnode)

    return topnode

def get_testsuites(node, maxlevel=1000):
    """
    get_testsuites traverses a node tree (optionally to
    a specified depth) and returns a list of testsuites found.

    Input:
      node:     The 'root' of a result_node_tree
      maxlevel: The max dept to traverse down the tree. I.e. if maxlevel is
              reached

    Output:
      a list of result_nodes
    """
    nodelist = []

    if isinstance( node, suite_result) or node.root == True:
        # Check for children which are suite_results

        if isinstance( node, suite_result):
            nodelist.append(node)

        # Check the note for potential suite children
        if node.level < maxlevel:
            for child in node.children:
                childlist = get_testsuites(child,maxlevel)
                for childnode in childlist:
                    nodelist.append(childnode)

    return nodelist

def get_testcases(node, maxlevel=1000):
    """
    get_testcases traverses a node tree (optionally to
    a specified depth) and returns a list of testcases found.

    Be aware that a teststep is also a testcase.
    Be aware that when a testcase node is found children of this node are ignored
    Be aware that nodes of type suite_setup and suite_teardown are not traversed

    Input:
      node:     The 'root' of a result_node_tree
      maxlevel: The max dept to traverse down the tree. I.e. if maxlevel is
              reached

    Output:
      a list of result_nodes
    """

    if isinstance( node, testcase_result):
        return [node]
    if isinstance( node, suite_setup ) or isinstance( node, suite_teardown):
        return []
    if node.level == maxlevel:
        return [node]

    nodelist = []
    for child in node.children:
        childlist = get_testcases(child,maxlevel)
        for childnode in childlist:
            nodelist.append(childnode)

    return nodelist

def get_teststep_count(node):
    """
    get_teststep_count returns the number of teststeps (aka leaves)
    found in the node tree given

    Input:
      node: The result_node to traverse

    Output:
      a number
    """

    if isinstance( node, teststep_result):
        return 1

    cnt = 0
    for child in node.children:
        cnt += get_teststep_count(child)

    return cnt

def get_key(node, key):
    """
    get_output traverses a nodetree to find all nodes containing
    a specific key entry (like e.g. output)

    Input:
      node: The result_node to traverse
      key:  a string

    Output:
      list of result_nodes
    """
    nodelist = []
    if key in node.result:
        nodelist.append(node)
    for child in node.children:
         childlist = get_key(child, key)
         for childnode in childlist:
             nodelist.append(childnode)

    return nodelist


def sort_results(node, recursive=True, level=0):
    """
    sort_results sort the result children nodes according to their start_time tag
    """
    node.children.sort(key=attrgetter('start_time'))

    if recursive:
        for child in node.children:
            sort_results(child, level=level +1)

def clean_count_or_retry(node):
    """
    Traverses the tree. If a node has children of
    type count_or_retry all but the last are removed
    """
    try:
        child = node.children[-1]

    except:
        # No children
        return

    if isinstance(child, count_or_retry):
        node.children = []
        node.add_child(child)

    for child in node.children:
        clean_count_or_retry(child)

def uniq_name(node, recursive=True, level=0):
    """
    Make the names of the nodes uniq by adding a dynamic
    number.
    """
    base_name = node.name
    counter = 1
    while base_name in uniq_name_list:
        # Name already exist - rename and add to list
        base_name = node.name+"-d%s"%(counter)
        counter+=1

    node.name = base_name
    uniq_name_list.append(node.name)

    if recursive:
        for child in node.children:
            uniq_name(child, level=level +1)


def niceprint(node, recursive=True, level=0):
    """
    niceprint is mostly for debug. It can be used to make a human
    readable output of a node or nodetree.
    """
    indent = '    ' * level
    print '%s============================================'%(indent)
    print '%sName: %s'%(indent, node.name)
    #if not type(node) == result_node:
    print '%sResult: %s'%(indent, node.result['result'])
    print '%sType: %s'%(indent, node.__class__.__name__)
    print '%sPath: %s'%(indent, node.path)
    print '%s# of children: %s'%(indent, len(node.children))
    print '%s# of teststeps: %s'%(indent, get_teststep_count(node))
    print '%sstarttime: %s'%(indent, node.start_time)
    print '%s============================================'%(indent)

    if recursive:
        for child in node.children:
            niceprint(child, level=level +1)


def niceprint_suites(node, recursive=True, level=0):
    """
    niceprint_suites is mostly for debug. It can be used to make a human
    readable output of a node or nodetree.
    """

    if isinstance( node, suite_result):
        indent = '    ' * level
        print '%s============================================'%(indent)
        print '%sName: %s'%(indent, node.name)
        print '%sResult: %s'%(indent, node.result['result'])
        print '%sType: %s'%(indent, node.__class__.__name__)
        print '%sPath: %s'%(indent, node.path)
        print '%s# of children: %s'%(indent, len(node.children))
        print '%s# of teststeps: %s'%(indent, get_teststep_count(node))
        print '%s============================================'%(indent)

    # Recursive into sub nodes in case of suite or root
    if isinstance( node, suite_result) or node.root == True:
        if recursive:
            for child in node.children:
                niceprint_suites(child, level=level +1)



def headerprint(node, recursive=True, level=0):
    """
    headerprint is mostly for debug. It can be used to show a one-liner
    for a node or a nodetree (one line pr node)
    """
    indent = '    ' * level
    #if type(node) == result_node:
    #    res="----"
    #else:
    res= node.result['result']
    print '%sResult: %s (%s)  Name: %s'%(
             indent, res, get_teststep_count(node), node.name)
    if recursive:
        for child in node.children:
            headerprint(child, level = level + 1)


def runtest():

    # test code
    testnode = generate_node_tree("result/latest")

    print 'Entire node tree (long form): '
    niceprint (testnode)

    print '#' * 80
    print 'All suites from the node tree  (long form): '
    niceprint_suites(testnode)

    print '#' * 80
    print 'Entire node tree (short form): '
    headerprint(testnode)
    print '#' * 80

    print 'All test suites (max level):'
    test_suites = get_testsuites(testnode)
    for node in test_suites:
        headerprint(node, False, node.level)
    print '---- Testsuite total: %s'%(len(test_suites))
    print '#' * 80

    print 'All testcases (max level):'
    test_cases = get_testcases(testnode)
    for node in test_cases:
        headerprint(node, False, node.level)

    print '---- Testcase total: %s'%(len(test_cases))

    print '#' * 80
    print '#' * 80
    print 'All testcases (level 2):'
    test_cases = get_testcases(testnode, 2)
    for node in test_cases:
        headerprint(node, False, node.level)

    print '---- Testcase total: %s'%(len(test_cases))

    print '#' * 80
    print '#' * 80
    print 'All testcases (level 1):'
    test_cases = get_testcases(testnode, 1)
    for node in test_cases:
        headerprint(node, False, node.level)

    print '---- Testcase total: %s'%(len(test_cases))

    print '#' * 80
    print '#' * 80

    print 'All testcases with metric (level 3): '
    test_cases = get_testcases(testnode,3)
    for node in test_cases:
        outputlist = get_key(node, 'output')
        if len(outputlist) > 0:
            print ''
            print 'Testcase: %s'%(node.name)

        for outputnode in outputlist:
            output = outputnode.result['output']

            if 'metric' in output:
                res = 'metric: ' + output['metric']
            else:
                res = ' NO metric'
            print '    Node: %s, output: %s'%(outputnode.name, res)


if __name__ == "__main__":
    runtest()
