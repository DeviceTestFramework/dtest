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

import yaml
import os
import glob
import datetime
import logging
import codecs
import shlex, subprocess # Cmdline splitting
import result_parse
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import seaborn as sns

import logging
import re

logger = logging.getLogger("ReportGenrator")

def sys_cmd_get_stdout(self, command_line):
    """
    Run system command - expect 0 as return code else assert
    Returning stdout
    """

    args = shlex.split(command_line)
    process = subprocess.Popen(args,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # wait for the process to terminate
    out, err = process.communicate()
    logging.info("Stdout:\n'" + out + "'\n")
    logging.info("Stderr:\n'" + err + "'\n")

    errcode = process.returncode
    logging.info("Return code is: " +   str(errcode))
    if errcode != 0:
        logging.error("Stdout:\n'" + out + "'\n")
        logging.error("Stderr:\n'" + err + "'\n")
        self.assertEqual(errcode,0,msg="subprocess returned " + str(errcode) + ". Expecting 0")

    # Version is in the output
    # Remove the trailing line sep
    return out.rstrip('\n')

class TestSetup():
    ''' Class to hold information about the test setup  '''
    def __init__(self, config_file=None):
        if config_file is None:
            logger.info("Config file not given - using standard values")
        else:
            logger.info("Config file given - loading it")
            self.config = yaml.load(file(config_file,'r'))

    def get(self,key):
        try:
            value = self.config[key]
        except KeyError:
            logger.warning("Could not find key '%s' in configuration!"%(key))
            value =None
        return value

class AsciiDoc():
    ''' Get some string which can be used in asciidoc - so fare just returning the strings '''
#    def __init__(self):
#        self.init=True

    def get_version(self):
        """
        Get the version of asciidoc
        """
        command_line = "asciidoc --version"
        args = shlex.split(command_line)
        process = subprocess.Popen(args,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # wait for the process to terminate
        out, err = process.communicate()
        logging.info("Stdout:\n'" + out + "'\n")
        logging.info("Stderr:\n'" + err + "'\n")

        errcode = process.returncode
        logging.info("Return code is: " +   str(errcode))
        if errcode != 0:
            logging.error("Stdout:\n'" + out + "'\n")
            logging.error("Stderr:\n'" + err + "'\n")
            self.assertEqual(errcode,0,msg="subprocess returned " + str(errcode) + ". Expecting 0")

        # Version is in the output
        return out

    def header(self,name, level):
        level_indicator  = '=' * (level+1)
        return "\n%s %s"%(level_indicator,name)

# Test af level function  - move to ascii doc class
#        for level in range(1,5):
#            self.output_writeline( AsciiDoc().header( "Level %d"%level , level))




class ReportGenerator():
    def __init__(self, result_dir="result/latest", report_name='report.html', tmp_dir=None, config_file=None, report_args=None):
        ''' Init the report generation:
        Input:
        - result_dir: The directory to traverses for test results
        - report_name: The name of the report to generate
        - tmp_dir: directory used for tmp file, e.g. the intermedian asciidoc file
        - config_file: Yaml Config file which provides information about the test setup
        - report_args: List of additional args - currently not used!
        '''

        if result_dir is None:
            raise AssertionError("result_dir must be given!")

        self.result_dir = result_dir;
        self.tmp_dir = tmp_dir;
        self.report_name=report_name;
        self.config_file=config_file;
        self.outStream=None
        self.versionInformationFile= os.path.abspath("doc/VersionInformation.txt")
        self.write_test_case_summery = False # Do not give a test case overview

        # The result dir to process must exist
        if not (os.path.exists(self.result_dir)):
            raise AssertionError("Result dir '" + self.result_dir + "' does not exist")

        # The tmp dir is needed to store tmps
        if not (os.path.exists(self.tmp_dir)):
            raise AssertionError("tmp dir '" + self.tmp_dir + "' does not exist")

        # Do not allow to overwrite previous report
        if(os.path.exists(self.report_name)):
            logger.warning("Overwrite previous report!")
#            raise AssertionError("Report: '" + self.report_name   + "' already exists - I do not dare to overwrite.. ")

        # Tmp report files goes to the tmp dir
        self.tmp_report_file = os.path.join(self.tmp_dir, self.report_name) +  ".asciidoc"
        logger.debug("The temp report file is %s"%self.tmp_report_file)

        if not (os.path.exists(self.versionInformationFile)):
            raise AssertionError("Version information file'" + self.versionInformationFile + "' does not exist")

        # Any config file?
        if not self.config_file is None:
            if not (os.path.isfile(self.config_file)):
                raise AssertionError("Config file ('%s') does not exists! Report: "%self.config_file)


        self.testSetup = TestSetup(self.config_file)


    def output_open(self):
        self.outStream = codecs.open(self.tmp_report_file,'w',encoding="utf8")

    def output_writeline(self,line):
        if self.outStream is None:
            raise AssertionError("outStream not yet available!")
        self.outStream.write(line+os.linesep)

    def output_write(self,text):
        if self.outStream is None:
            raise AssertionError("outStream not yet available!")
        self.outStream.write(text)

    def report_gen(self):
        logger.info("Report generation based on the results in %s", self.result_dir)
        logger.info("asciidoc version is: '%s'"%(AsciiDoc().get_version()))

        self.output_open()
        self.gen_report_header()

        self.gen_report_body()

        self.gen_report_footer()

        # Convert the file to html
        # decode the doc type from the file name
        extension = os.path.splitext(self.report_name)[1]
        logger.debug("Extension is %s"%extension)
        if extension == ".html":
            doctype="html5"
        elif extension == ".pdf":
            doctype="pdf"
        elif extension == ".db":
            doctype = "docbook45"
        else:
            raise AssertionError("Unsupported doc type '%s'. Supported are: html/pdf/db"%extension)

        command_line = "asciidoc -b %s --out-file=%s %s "%(doctype,self.report_name, self.tmp_report_file )
        directory =  os.getcwd()
        args = shlex.split(command_line)

        logger.debug("Try to run %s in %s"%(args,directory))

        process = subprocess.Popen(args, cwd=directory,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # wait for the process to terminate
        out, err = process.communicate()
        logging.info("Stdout:\n'" + out + "'\n")
        logging.info("Stderr:\n'" + err + "'\n")

        errcode = process.returncode
        logging.info("Return code is: " +   str(errcode))
        if errcode != 0:
            logging.error("Process running %s in %s failed!!!"%(args,directory))
            logging.error("Stdout:\n'" + out + "'\n")
            logging.error("Stderr:\n'" + err + "'\n")
            self.assertEqual(errcode,0,msg="subprocess returned " + str(errcode) + ". Expecting 0")



    def gen_report_header(self):
        ''' Function to generate the header of report '''
        self.output_writeline( AsciiDoc().header(self.testSetup.get('title'), 0) )
        self.output_writeline(":Author: "+self.testSetup.get('author'))
        self.output_writeline(":Email: "+self.testSetup.get('email'))
        self.output_writeline(":Date: "+datetime.datetime.now().strftime("%d-%m-%Y"))
        self.output_writeline(":toc2:")
        self.output_writeline(":toclevels: 5")
        self.output_writeline("")
        self.output_writeline("[big]#Customer: "+self.testSetup.get('customer')+"#")
        self.output_writeline("")
        self.output_writeline("[big align=right]#Device under test: "+self.testSetup.get('board')+"#")
        self.output_writeline("")


    def get_color(self, result_txt):
        '''Returns the color to use for the specified result'''
        if (result_txt == "PASS"):
            color = 'green'
        elif (result_txt == "SKIP"):
            color = 'olive'
        else:
            color = 'red'
        return color

    def gen_report_footer(self):
        ''' Function to generate the footer of report '''
        #self.output_writeline("Modify footer if needed... ")

    def print_table_header(self, node):
        """
        Print the first row of the table
        """

        child = node
        print_layout="table"

        table = ""
        table += '[options="",cols="<30%strong,<52%m,^8%m,^10%m"]'+"\n"
        table += "|====="+"\n"
        table += ".2+.^|"+" Name"+" .2+^.^|"+child.name+"|"
        if 'retries' in child.result:
            table += "retries"
        else:
            table += "runs"
        table+= "|status"+"\n"

        if 'retries' in child.result:
            runs = child.result['retries']
            max_runs = child.result['retry-max']
            table += "|%s/%s"%(runs,max_runs)
        else:
            try:
                runs = child.result['count']
            except:
                runs = 1
            table += "|%s"%(runs)

        table += "|[%s big]"%self.get_color(child.result['result'])
        table += "*%s*\n"%(child.result['result'])

        return table

    def print_suite_link_table(self,node):
        """
        Print a table with a link to the details
        """
        child=node

        table = self.print_table_header(node)

        # Id +  link:
        table += "|Id 3+a|xref:%s[%s]\n" %(id(child),child.name)
        # Span two cols

        table += "|====="+"\n"
        self.output_write(table)

    def print_teststep_table(self,node,params_remove_list=None,params_keep_list=None):

        child=node
        remove_list=params_remove_list
        keep_list=params_keep_list
        logger.debug('Writting this child on bullet form %s'%child.name)


        try:
            description = child.result['description']
            logger.debug("Found the following description from child '%s'"%description)
        except:
            description=""

        try:
            params=child.result['params']
            logger.debug("Found the following params from child '%s'"%params)
        except:
            params=None

        # Do some filtering here - e.g. only keep the params we really like, or filter out some we do not like
        if params:
            # Delete remove keys:
            for remove_item in remove_list:
                try:
                    del params[remove_item]
                except:
                    pass

            # Only keep the keys listed in keep
            if keep_list:
                # Loop over each key in params - delete all which are not present in the keep list
                import copy
                # Make a deep copy
                tmpparams =   copy.deepcopy(params)

                for key in tmpparams:
                    if key not in keep_list:
                        print "deleting non-keep key"
                        logger.debug("Deleting key: %s from the params list"%(key))
                        del params[key]


        table = self.print_table_header(child)

        # put 3+l to make it span 3 cols and make it a literalblock
        table += "|Description 3+l|"+description+"\n"

        # Id:
        table += "|Id 3+|"+child.name+"\n" # Span 3 cols

        if params:
            logger.debug("Child: %s has the following params: '%s'"%(child.name, params))
            #Loop the parameters to print them on individual lines - change the style to asciidoc (indicated with a|)
            table += "|Parameters 3+a|" # Span 3 cols
            for key in params:
                logger.debug("Param: '%s': '%s'"%(key,params[key]))
                # Escape '|'
                table += " * %s: %s\n"%(key,str(params[key]).replace('|','\|'))
        table += "|====="+"\n"
        self.output_write(table)

    def node_is_suite(self,node):
        """
        Test suites of type "setup" and "teardown" could be steps/cases/suites
        This function guess the actual case. Return True if it thinks the node is a suite else false
        """
        if isinstance( node, result_parse.suite_result):
            return True

        if isinstance( node, result_parse.suite_setup) or isinstance( node, result_parse.suite_teardown):
            if result_parse.get_teststep_count(node) < 1 and len(node.children) == 0:
                logger.debug("Not a suite %s"%(node))
                return False
            return True
        else:
            return False

    def niceprint_suite_child(self, node, result_parse, remove_list, keep_list):
        # Check for setups
        # Check for teardown
        if isinstance( node, result_parse.teststep_result):
            # We have a test step - print them
            printtable = 0
            if not printtable:
                self.print_teststep_table(node,params_remove_list=remove_list, params_keep_list=keep_list)

            else:
                # Print in a table with the step data
                self.output_writeline('')
                self.output_writeline(".%s"%node.name)
                self.output_writeline('[width="100%",cols="2,10"]')
                self.output_writeline('[frame="topbot",grid="none"]')

                logger.debug('Print suite test step of name %s'%node.name)

                self.output_writeline('|======')
                color = self.get_color(node.result['result'])
                self.output_writeline('|Verdict:|[%s big]#%s#'%(color,node.result['result']))
                try:
                    self.output_writeline('|Description:|%s'%(node.result['description']))
                except:
                    logger.warning("Could not give description for %s"%node.name)

                    self.output_writeline('|======')
                    self.output_writeline('')
        elif isinstance( node, result_parse.suite_result):
            # A result - create a link to that suite then
            # Syntax "xref:anchor-2[Second anchor]"
            #self.output_writeline("* %s: xref:%s[Details]"%(child.name, id(child)))
            self.print_suite_link_table(node)

        elif isinstance( node, result_parse.testcase_result):
            self.print_teststep_table(node,params_remove_list=remove_list, params_keep_list=keep_list)
#            self.output_writeline("* Testcase result: %s"%(node.name))
        elif isinstance( node, result_parse.suite_setup):
            # If that suite does have any step
            # We have a setup, but it could be a suite/step or case. Make a qualified guess
            # No children - then it is a step - print it
            if self.node_is_suite(node):
#                self.output_writeline("* Suite setup: %s: xref:%s[Details]"%(node.name, id(node)))
                self.print_suite_link_table(node)
            else:
                self.print_teststep_table(node,params_remove_list=remove_list, params_keep_list=keep_list)


        elif isinstance( node, result_parse.suite_teardown):
            if self.node_is_suite(node):
               #self.output_writeline("* Suite setup: %s: xref:%s[Details]"%(child.name, id(child)))
               self.print_suite_link_table(node)
            else:
                self.print_teststep_table(node,params_remove_list=remove_list, params_keep_list=keep_list)

#            self.output_writeline("* Suite teardown: %s"%(node.name))
        elif isinstance( node, result_parse.count_or_retry):
            for child in node.children:
                self.niceprint_suite_child(child, result_parse, remove_list, keep_list)
        else:
            self.output_writeline("* NOT teststep or suite result!!!%s  %s %s"%(node, node.name, type(node)))
            raise AssertionError("Unknown type - I do not know how to handle it!")

    def niceprint_suites_headings(self, node, recursive=True, level=0):

        """
        niceprint is mostly for debug. It can be used to make a human
        readable output of a node or nodetree.
        """
        if isinstance( node, result_parse.count_or_retry):
            for child in node.children:
                self.niceprint_suites_headings(child, recursive, level)

        if (isinstance( node, result_parse.suite_result) or
            isinstance( node, result_parse.suite_setup) or
            isinstance( node, result_parse.suite_teardown) or
            node.level == 0):
            if not node.level is 0:

                asciidoc_header_level = max(min(4,level+1),2)

                # Is is a suite? Then print headers
                if self.node_is_suite(node):

                    # Create the header and include an anchor - syntax is [[anchor-1]]. Use the node ID as the anchor to get a
                    # uniq id
                    self.output_writeline( AsciiDoc().header( "%s"%(node.name) , asciidoc_header_level) + "[[%s]]"%(id(node)) )
                    self.output_writeline('....')
                    try:
                        self.output_writeline( node.result['description'] )
                    except:
                        logger.debug("No description given for %s"%(node.name))
                    self.output_writeline('....')

                    if node.parent.level > 0 :
                        self.output_writeline("xref:%s[up]"%(id(node.parent)))


                logger.debug("Print steps if any for %s"%(node.name))
                if result_parse.get_teststep_count(node) == 0:
                    logger.debug("# %s for %s"%(result_parse.get_teststep_count(node),node.name))
                    logger.debug("Children %s"%(node.children))
                    logger.debug("Node %s"%(node))
                if result_parse.get_teststep_count(node) > 0:
                    logger.debug("# %s for %s"%(result_parse.get_teststep_count(node),node.name))
                    # Print test steps
                    #self.output_writeline( AsciiDoc().header( "Steps:" , asciidoc_header_level+1) )
                    #self.output_writeline('')

                    # Get the parameter filter settings from the setup file
                    # Initialize the lists - per default do no filtering
                    remove_list = []
                    keep_list =  [] # Empty list means "keep all"
                    filter_params = self.testSetup.get('filter_params')
                    if filter_params is not None:
                        logger.debug("filter_params given in configuration file")
                        remove_list = filter_params.get('remove',[])
                        keep_list =  filter_params.get('keep',[])
                        logger.debug("remove list: %s"%(remove_list))
                        logger.debug("keep list: %s"%(keep_list))
                    else:
                        logger.warning("no filter_params given in configuration file - you may see too many params in the report!")

                    # List each step:
                    for child in node.children:
                        self.niceprint_suite_child(child, result_parse, remove_list, keep_list)

                    self.output_writeline('')

            if recursive:
                for child in node.children:
                    logger.debug("Running recursive for child %s (name %s)"%(child, child.name))
                    self.niceprint_suites_headings(child, level=level +1)


    def niceprint_suites(self, node, recursive=True, level=0):

        """
        niceprint is mostly for debug. It can be used to make a human
        readable output of a node or nodetree.
        """
        #print node.__class__.__name__, node.level, node.name

        if isinstance( node, result_parse.suite_result) or node.level == 0:
            if node.level > 0:
                #print '%s,%s,%s,%s,%s'%(node.name, node.result['result'], result_parse.get_teststep_count(node),len(node.children), node.__class__.__name__)
                desc =  node.result.get('description','N/A')
                color = self.get_color(node.result['result'])
                self.output_writeline('|%s|[%s big]#%s#|%s|%s|%s'%(node.name, color, node.result['result'], result_parse.get_teststep_count(node),len(node.children),desc))
                #print node.result['description']

            if recursive:
                for child in node.children:
                    self.niceprint_suites(child, level=level +1)

    def niceprint_overview_suites(self, node, recursive=True, level=0, maxdepth=9999,mindepth=1):

        """
        niceprint is mostly for debug. It can be used to make a human
        readable output of a node or nodetree.
        """
        #print node.__class__.__name__, node.level, node.name

        if isinstance( node, result_parse.suite_result) or node.level == 0:
            #print 'Inside: %s,%s,%s,%s,%s'%(node.name, node.result['result'], result_parse.get_teststep_count(node),len(node.children), node.__class__.__name__)
            if node.level > mindepth:
                desc =  node.result.get('description','N/A')
                color = self.get_color(node.result['result'])
                self.output_writeline('a|xref:%s[%s %s]|[%s big]#%s#|%s'%(id(node),"--"*(level-1),node.name, color, node.result['result'], desc))

            if recursive and maxdepth > node.level:
                for child in node.children:
                    self.niceprint_overview_suites(child, level=level +1, maxdepth=maxdepth, mindepth=mindepth)
        elif isinstance (node, result_parse.count_or_retry):
            if recursive and maxdepth > node.level:
                for child in node.children:
                    self.niceprint_overview_suites(child, level=level, maxdepth=maxdepth, mindepth=mindepth)

    def check_benchmark(self, outputlist):
        """ Check if there are benchmarks in the test results """

        for outputnode in outputlist:
            output = outputnode.result['output']

            if isinstance(output, dict) and 'metric' in output:
                # There is a least one metric break
                return True

        return False

    def gen_benchmark(self, testnodeall):
        """
        Generate a section with benchmarks in case the tests did contain any benchmarks.
        """

        outputlist = result_parse.get_key(testnodeall, 'output')

        if not self.check_benchmark(outputlist):
            logger.debug("No benchmarks detected - returning from gen_benchmark")
            return

        self.output_writeline( AsciiDoc().header( "Benchmark results", 2) )

        self.output_writeline('[options="header",width="100%",cols="2*4<a,2<a,10<l"]')
        self.output_writeline('|=======================')
        self.output_writeline('|Benchmark name|Metric| Value |Unit')

        for outputnode in outputlist:
            output = outputnode.result['output']
            logger.debug("Benchmark output print able: '%s'"%(repr(output)))

            if isinstance(output, dict) and 'metric' in output:
                name=output['metric']
                unit=output['unit']
                value=float(output['value'])
                precision="2"
                if (value) > 10:
                    precision="3"
                if (value) > 1000:
                    precision="4"
                if (value) > 1000000:
                    value = value / 1000000
                    unit += ' (millions) '
                    precision="3"

                fmt = "|%s|%s|%."+ precision + "g|%s"
                self.output_writeline(fmt%(outputnode.name,name,value,unit))

        self.output_writeline('|=======================')
        self.output_writeline('')

    def gen_benchmark_plots(self, testnodeall):
        """ Generate a section with plot figures for each benchmark """

        outputlist = result_parse.get_key(testnodeall, 'output')
        dut_id = self.testSetup.get('board').lower().replace(' ', '_')

        # don't do plots if no benchmarks are found
        if not self.check_benchmark(outputlist):
            logger.debug("No benchmarks detected - returning from gen_benchmark_plots")
            return

        for outputnode in outputlist:
            output = outputnode.result['output']

            if not isinstance(output, dict) or not 'metric' in output:
                continue

            metric_id = output['metric'].lower().replace(' ', '_')
            filename = "{}_{}.png".format(dut_id, metric_id)
            plots_folder = "plots"
            path = os.path.join(plots_folder, filename)

            if not os.path.exists(path):
                logger.debug("Skipping metric: plot does not exist: {}".format(path))
                continue

            print(path)
            self.output_writeline("image::{}[{}]".format(path, metric_id))

    def gen_sw_setup(self, testnodeall):
        """
        Read the SW setup from the target based.
        The output in result.yaml has a key word which make us print this

        The following format is expected:
output: {bl-version: 'U-Boot 2013.10-00036-g9c1f617 fo (Aug 06 2014 - 08:42:09)',
  dl-version: 'Linux-3.8.13--00758-g489d471 (Jul 11 2014 - 08:00:18)', image_versions: "Image\
    \ versions:\r\n  Bootloader image: U-Boot 2013.10-00036-g9c1f617 fo (Aug 06 2014\
    \ - 08:42:09)\r\n  Download image:   Linux-3.8.13--00758-g489d471 (Jul 11 2014\
    \ - 08:00:18)\r\n  System image:     Linux-3.8.13-4e04ee9-dirty-00760 (Aug 06\
    \ 2014 - 08:05:15)", sys-version: 'Linux-3.8.13-4e04ee9-dirty-00760 (Aug 06 2014
    - 08:05:15)'}

        The above is test run of - dctrl.linux.dboot-info:
        """

        has_sw_information = False
        magic_key = 'image_versions' # Primary key to search for
        # Currently we print image_versions directly, but these below can also be used:
        magic_search_words = ['bl-version','dl-version','sys-version']

        # Check if there are benchmarks in the test results
        outputlist = result_parse.get_key(testnodeall, 'output')
        for outputnode in outputlist:
            output = outputnode.result['output']
            if isinstance(output, dict) and magic_key in output:
                # There is a least one test case with information regarding the version -> break
                has_sw_information=True
                break

        if not has_sw_information:
            logger.warning("No tests with SW version detected - returning from gen_sw_setup")
            return

        self.output_writeline( AsciiDoc().header( "DUT SW details", 2) )
        output = outputnode.result['output']
        # Print it literral
        self.output_writeline('....')
        self.output_writeline(output[magic_key])
        self.output_writeline('....')
        self.output_writeline('')


    def gen_report_body(self):
        ''' Function to generate the body of report. i.e. the actual content '''

        # Grep test information!
        testnodeall =  result_parse.generate_node_tree(self.result_dir, uniq_names=True, keep_multiple_runs=False)

        #result_parse.niceprint_suites(testnodeall)

        ########## Setup     #####################
        # Generate the setup e.g. hw/sw setup
        self.output_writeline( AsciiDoc().header( "Setup", 1) )
        self.output_writeline("This section will present the main-equipment and software used in order to conduct the test.")

        ########## Equipment #####################
        self.output_writeline( AsciiDoc().header( "Equipment", 2) )
        equipment = self.testSetup.get('equipment')
        if equipment is None:
            raise AssertionError("No equipment listed in the config file!")

        # Generate a bullet list with the equipment used
        for key in equipment:
            logger.debug("Equipment: '%s': '%s'"%(key,equipment[key]))
            self.output_writeline(" * %s: %s"%(key,equipment[key]))

        ########## Software ######################
        self.output_writeline( AsciiDoc().header( "Software", 2) )
        software = self.testSetup.get('software')
        if software is None:
            raise AssertionError("No software listed in the config file!")

        # Generate a bullet list with the software used
        for key in software:
            logger.debug("Software: '%s': '%s'"%(key,software[key]))
            self.output_writeline(" * %s: %s"%(key,software[key]))

        self.gen_sw_setup(testnodeall)


        self.output_writeline( AsciiDoc().header( "Summary", 1) )
        self.output_writeline('[options="header",width="100%",cols="4<a,2<a,10<l"]')
        self.output_writeline('|=======================')
        self.output_writeline('|Test Suite name|Verdict| Description')

        #generate summay section
        for testnode in testnodeall.children:
            self.niceprint_overview_suites(testnode, maxdepth=1, mindepth=0)
        self.output_writeline('|=======================')
        self.output_writeline('')

        self.gen_benchmark(testnodeall)
        self.gen_benchmark_plots(testnodeall)

        #elaborate on summary section
        for testnode in testnodeall.children:
            test_cases = result_parse.get_testcases(testnode)
            testsuites = result_parse.get_testsuites(testnode, 1)
            logger.debug("Do test suites")

            if not testsuites:
                logger.warning("There are no testsuites!")
                continue

            self.output_writeline( AsciiDoc().header( "Test Suite - "+testsuites[0].name , 1) )
            self.output_writeline( testsuites[0].result.get('description','No description available'))
            self.output_writeline('.Test Suites ' )
            self.output_writeline('[options="header",width="100%",cols="4<a,2<a,10<l"]')
            self.output_writeline('|=======================')
            self.output_writeline('|Test Suite name|Verdict| Description')

            self.niceprint_overview_suites(testnode)

            self.output_writeline('|=======================')

            self.output_writeline('')

            if self.write_test_case_summery:
                self.output_writeline( AsciiDoc().header( "Test Cases" , 2) )

                self.output_writeline('')
                self.output_writeline('.Test cases ' )
                self.output_writeline('[width="90%",cols="4,2,10"]')
                self.output_writeline('[frame="topbot",grid="none"]')
                self.output_writeline('|======')


                for node in test_cases:
                    outputlist = result_parse.get_key(node, 'output')

                    testcase_description=""
                    try:
                        testcase_description = node.result['description']
                    except:
                        logger.warning('No description for %s'%(node.name))

                    color = self.get_color(node.result['result'])
                    # Name | Result | Description
                    self.output_writeline('|%s|[%s big]#%s#|%s'%(node.name, color,node.result['result'],testcase_description))

                self.output_writeline('|======')
                self.output_writeline('')

        # Appendix table setup - enables the coloring of background:
        # The setup is only needed once
        table = ""
        table += ":tabletags-yellow.bodydata: <td style='background-color:yellow;'>|</td>\n:tabledef-default.yellow-style: tags='yellow'\n"
        table += ":tabletags-silver.bodydata: <td style='background-color:silver;'>|</td>\n:tabledef-default.silver-style: tags='silver'\n"
        self.output_write(table)


        #appendix - output everything
        self.output_writeline( AsciiDoc().header( "Appendix - All tests in detail" , 1) )

        self.output_writeline("""The appendix present the conduct tests in more details.
        The tests may consist of more levels, i.e. a test has a sub-test and the sub-test may
        even have a sub-test below.
        Each test is presented with the following attributes:
        \n
         * Name
         * Id
         * Description
         * Pass/Fail (Did the test pass or fail - a pass could also be to expect a failure and get a failure)
         * Runs (The number of times this step was conducted. The sub-tests are also run as many times)
         * Retries (A suite or test case allowed to be repeated a certain number of times to produce a pass.
The number of attempts and the max allowed attempts are shown)
        \nSome tests also presents potential parameters used. E.g. the command: "dupdate-boot" has the parameter "mode:bl" to indicate that the board should boot in bootloader mode.
        In case the test has sub-tests then the Id is a link. If the link is followed one will see
the steps in the sub-test. In order to get back to the level above the "up" links can be used to get back.
        """)

        logger.debug("Run niceprint_suites_headings ")
        self.niceprint_suites_headings(testnodeall)

        ########## Version information ###########
        self.output_writeline( AsciiDoc().header( "Appendix - Version information" , 1))

        self.output_writeline("Version information regarding the test environment, test suites and test cases.")

        self.output_writeline( AsciiDoc().header( "Current Version" , 2))

        self.output_writeline(" * test:")
        self.output_writeline(" ** %s . %s"%(sys_cmd_get_stdout(self,"git rev-parse HEAD "),sys_cmd_get_stdout(self,"git describe --all")))

        self.output_writeline(" * submodules:")
        git_submodule_info = sys_cmd_get_stdout(self,"git submodule status")
        for line in git_submodule_info.splitlines():
            self.output_writeline(" ** %s"%(line))

        self.output_writeline("include::%s[]"%self.versionInformationFile)

class StoreMetrics():
    def __init__(self, result_dir="result/latest", report_name='metrics.csv', tmp_dir=None, config_file=None, report_args=None):
        ''' Init the store metrics:
        Input:
        - result_dir: The directory to traverses for test results
        - report_name: The name of the report to generate
        - tmp_dir: directory used for tmp file, e.g. the intermedian asciidoc file
        - config_file: Yaml Config file which provides information about the test setup
        - report_args: List of additional args - currently not used!
        '''

        if result_dir is None:
            raise AssertionError("result_dir must be given!")

        self.result_dir = result_dir;
        self.tmp_dir = tmp_dir;
        self.report_name=report_name;
        self.config_file=config_file;
        self.outStream=None
        self.write_test_case_summery = False # Do not give a test case overview

        # The result dir to process must exist
        if not (os.path.exists(self.result_dir)):
            raise AssertionError("Result dir '" + self.result_dir + "' does not exist")

        # The tmp dir is needed to store tmps
        if not (os.path.exists(self.tmp_dir)):
            raise AssertionError("tmp dir '" + self.tmp_dir + "' does not exist")

        # Tmp report files goes to the tmp dir
        self.tmp_report_file = os.path.join(self.tmp_dir, self.report_name) +  ".tmp"
        logger.debug("The temp report file is %s"%self.tmp_report_file)

        # Any config file?
        if not self.config_file is None:
            if not (os.path.isfile(self.config_file)):
                raise AssertionError("Config file ('%s') does not exists! Report: "%self.config_file)

        self.testSetup = TestSetup(self.config_file)

    def output_open(self):
        self.outStream = codecs.open(self.tmp_report_file,'w',encoding="utf8")

    def output_writeline(self,line):
        if self.outStream is None:
            raise AssertionError("outStream not yet available!")
        self.outStream.write(line+os.linesep)

    def output_write(self,text):
        if self.outStream is None:
            raise AssertionError("outStream not yet available!")
        self.outStream.write(text)

    def report_gen(self):
        logger.info("Report generation based on the results in %s", self.result_dir)

        self.output_open()

        self.gen_report_body()

        # Convert the file to html
        # decode the doc type from the file name
        extension = os.path.splitext(self.report_name)[1]
        logger.debug("Extension is %s"%extension)
        if extension == ".csv":
            doctype="csv"
        else:
            raise AssertionError("Unsupported doc type '%s'. Supported are: csv"%extension)

        if(os.path.exists(self.report_name)):
            write_header = False
        else:
            write_header = True

        ftmprep = open(self.tmp_report_file, 'r')
        frep = open(self.report_name, 'a+b')
        if(write_header):
            frep.write('Dut,DateTime,Name,Metric,Value,Unit\n')
        frep.write(ftmprep.read())
        ftmprep.close()
        frep.close()

    def gen_benchmark(self, testnodeall):
        """
        Generate a section with benchmarks in case the tests did contain any benchmarks.
        """

        has_benchmark=False

        # Check if there are benchmarks in the test results
        outputlist = result_parse.get_key(testnodeall, 'output')
        for outputnode in outputlist:
            output = outputnode.result['output']
            if isinstance(output, dict) and 'metric' in output:
                # There is a least one metric break
                has_benchmark=True
                break

        if not has_benchmark:
            logger.debug("No benchmarks detected - returning from gen_benchmark")
            return

        for outputnode in outputlist:
            output = outputnode.result['output']
            logger.debug("Benchmark output print able: '%s'"%(repr(output)))

            if isinstance(output, dict) and 'metric' in output:
                name=output['metric']
                unit=output['unit']
                value=float(output['value'])
                precision="2"
                if (value) > 10:
                    precision="3"
                if (value) > 1000:
                    precision="4"
                if (value) > 1000000:
                    value = value / 1000000
                    unit += ' (millions) '
                    precision="3"

                fmt = "%s,%s,%s,%s,%."+ precision + "g,%s"
                self.output_writeline(fmt%(self.testSetup.get('board'),datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),outputnode.name,name,value,unit))

    def gen_report_body(self):
        ''' Function to generate the body of report. i.e. the actual content '''

        # Grep test information!
        testnodeall =  result_parse.generate_node_tree(self.result_dir, uniq_names=True, keep_multiple_runs=False)

        self.gen_benchmark(testnodeall)

    def gen_plots(self):
        ''' Function to plot benchmark results as png files for use in the generated report '''

        # settings
        plots_folder = "plots"
        plot_width = 8
        plot_height = 4

        if not os.path.exists(plots_folder):
            os.mkdir(plots_folder)

        # read the csv file into pandas data frame. Use column 1 as index (dates) and convert
        # these to datetime objects
        df = pd.read_csv(self.report_name, parse_dates=[1])

        # convert values to floats to make them usable in plots
        df['Value'] = df['Value'].apply(float)

        # order data into groups based on device under test and the tested metric
        groups = df.groupby(['Dut', 'Metric'])

        # state variables
        dut = None
        pdf_pages = None

        # for each (dut,metric)
        for name,group in groups:
            # Use datetime as index. Per group level to avoid duplicate times
            group.set_index('DateTime', inplace=True)

            # restart pdf_pages if new board
            if dut not in name:
                dut = name[0]
                dut_id = dut.lower().replace(' ', '_')

                # close pdf pages for previous board
                if pdf_pages:
                    pdf_pages.close()

                # create new pdf pages for current board
                p = "{}.pdf".format(dut_id)
                pdf_pages = PdfPages(os.path.join(plots_folder, p))

            # create new plot for each metric
            fig = plt.figure(figsize=(plot_width,plot_height))
            ax = fig.add_subplot(1,1,1)

            # plot the values vs. times
            group['Value'].plot(ax=ax, label=name[1])
            group['Value'].plot(ax=ax, style='o')

            # add titles to plot
            ax.set_title(name[1])
            ax.set_ylabel(group['Unit'][0])
            ax.set_xlabel('')

            # add padding to plot
            line = ax.get_lines()[0]
            y_max = line.get_ydata().min()
            y_min = line.get_ydata().max()
            ax.set_ylim(y_min * .9, y_max * 1.1)

            # save plot as png and add to pdf pages
            metric_id = name[1].lower().replace(' ', '_')
            filename = "{}_{}.png".format(dut_id, metric_id)

            fig.savefig(os.path.join(plots_folder, filename))
            pdf_pages.savefig(fig, transparent=True)

        # the last plot must be closed
        pdf_pages.close()
