# -*- coding: utf-8 -*-
#BEGIN_HEADER
import logging
import os

from Bio import SeqIO
from pprint import pprint, pformat
from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.DataFileUtilClient import DataFileUtil
from .CreateFasta_Report import CreateFasta
from .CreateFeatureLists_Report import CreateFeatureLists
from .CreateMultiGenomeReport import CreateMultiGenomeReport
from .Report_creator import Report_creator

#END_HEADER


class kb_ObjectInfo:
    '''
    Module Name:
    kb_ObjectInfo

    Module Description:
    A KBase module: kb_ObjectInfo
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = ""
    GIT_COMMIT_HASH = ""

    #BEGIN_CLASS_HEADER

    def get_assembly_sequence(self,assembly_input_ref):
        # Download the input data as a Fasta
        # We can use the AssemblyUtils module to download a FASTA file from our Assembly data object.
        # The return object gives us the path to the file that was created.
        print('Downloading Assembly data as a Fasta file.')
        assemblyUtil = AssemblyUtil(self.callback_url)
        fasta_file = assemblyUtil.get_assembly_as_fasta({'ref': assembly_input_ref})
        cf = CreateFasta(self.config)

        string = ''
        for seq_record in SeqIO.parse(fasta_file['path'], 'fasta'):
            string += ">" + seq_record.id + "\n"
            string += cf.splitSequence(str(seq_record.seq))
            string += "\n"

        return string

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
        logging.basicConfig(format='%(created)s %(levelname)s: %(message)s',
                            level=logging.INFO)
        self.workspaceURL = config['workspace-url']
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.dfu = DataFileUtil(self.callback_url)
        self.scratch = os.path.abspath(config['scratch'])
        self.config = config
        #END_CONSTRUCTOR
        pass


    def assembly_metadata_report(self, ctx, params):
        """
        This example function accepts any number of parameters and returns results in a KBaseReport
        :param params: instance of type "AssemblyMetadataReportParams" (A
           'typedef' can also be used to define compound or container
           objects, like lists, maps, and structures.  The standard KBase
           convention is to use structures, as shown here, to define the
           input and output of your function.  Here the input is a reference
           to the Assembly data object, a workspace to save output, and a
           length threshold for filtering. To define lists and maps, use a
           syntax similar to C++ templates to indicate the type contained in
           the list or map.  For example: list <string> list_of_strings;
           mapping <string, int> map_of_ints;) -> structure: parameter
           "assembly_input_ref" of type "assembly_ref", parameter
           "workspace_name" of String, parameter "showContigs" of type
           "boolean" (A boolean. 0 = false, other = true.)
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN assembly_metadata_report
        token = ctx['token']

        # Print statements to stdout/stderr are captured and available as the App log
        print('Starting Assembly MetaData Report Function. Params=')
        pprint(params)

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.
        print('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'assembly_input_ref' not in params:
            raise ValueError('Parameter assembly_input_ref is not set in input arguments')
        assembly_input_ref = params['assembly_input_ref']
        if 'showContigs' not in params:
            raise ValueError('Parameter showContigs is not set in input arguments')
        showContigs_orig = params['showContigs']
        showContigs = None
        try:
            showContigs = int(showContigs_orig)
        except ValueError:
            raise ValueError('Cannot parse integer from showContigs parameter (' + str(showContigs_orig) + ')')
        if showContigs < 0:
            raise ValueError('showContigs parameter cannot be negative (' + str(showContigs) + ')')
        if showContigs > 1:
            raise ValueError('showContigs parameter cannot be greater than one (' + str(showContigs) + ')')


        # Step 3 - Get the data and save the output to a file.
        data_file_cli = DataFileUtil(self.callback_url)
#        assembly_metadata = data_file_cli.get_objects({'object_refs': ['assembly_input_ref']})['data'][0]['data']
        assembly = data_file_cli.get_objects({'object_refs': [assembly_input_ref]})
        name = "Assembly Data Object"
        object_type = ''
        if 'info' in assembly['data'][0]:
            name = assembly['data'][0]['info'][1]
            object_type = assembly['data'][0]['info'][2]
        assembly_metadata = assembly['data'][0]['data']

        string = name + " Type=" + object_type  + "\n"
        string += "Data Columns are tab-delimited\n"
        dna_size = 1.0
        string += "METADATA\n"
        list = ['assembly_id', 'dna_size', 'gc_content', 'num_contigs',
                'fasta_handle_ref', 'md5', 'type', 'taxon_ref']
        for item in list:
            if item in assembly_metadata:
                string += "\t" + item + "\t" + str(assembly_metadata[item]) + "\n"
                if item == 'dna_size':
                    dna_size = assembly_metadata['dna_size']

        if 'fasta_handle_info' in assembly_metadata and 'node_file_name' in assembly_metadata['fasta_handle_info']:
            string += "\tfilename             = " + assembly_metadata['fasta_handle_info']['node_file_name'] + "\n"
        string += "\nDNA BASES\tCOUNTS\tPERCENT\n"
        pct = 1.00
        for base in assembly_metadata['base_counts']:
            pct = 100 * assembly_metadata['base_counts'][base] / dna_size
            string += "\t" + base + "\t" +  str(assembly_metadata['base_counts'][base]) + "\t" + str(pct) + "\n"

        string += "\nCONTIGS in the Assembly"
        string += "\nName\tLength\tGC content\tNum of Ns\tContigID\tDescription\n"
        if 'contigs' in assembly_metadata:
            myContig = assembly_metadata['contigs']
            for ctg in myContig:
                list = ['length', 'gc_content', 'Ncount', 'contig_id', 'description']
                string += ctg
                for item in list:
                    if item in myContig[ctg]:
                        string += "\t{}".format(myContig[ctg][item])
                    else:
                        string += "\t"
                string += "\n"

        if showContigs:
            string += "\nFASTA of the DNA Sequences\n"
            string += self.get_assembly_sequence(assembly_input_ref)

        report_path = os.path.join(self.scratch, 'assembly_metadata_report.txt')
        report_txt = open(report_path, "w")
        report_txt.write(string)

        report_txt.close()
        report_path = os.path.join(self.scratch, 'assembly_metadata_report.html')
        report_txt = open(report_path, "w")
        report_txt.write("<pre>" + string + "</pre>")
        report_txt.close()

        print (string)

        cr = Report_creator(self.config)
        reported_output = cr.create_report(token, params['workspace_name'],
                                    string, self.scratch)

        output = {'report_name': reported_output['name'],
                           'report_ref': reported_output['ref']}

        print('returning: ' + pformat(output))
        #END assembly_metadata_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method assembly_metadata_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def genome_report(self, ctx, params):
        """
        :param params: instance of type "GenomeReportParams" -> structure:
           parameter "genome_input_ref" of type "genome_ref", parameter
           "workspace_name" of String, parameter "report_format" of String
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN genome_report
        token = ctx['token']

        # Print statements to stdout/stderr are captured and available as the App log
        print('Starting Genome Report Function. Params=')
        pprint(params)

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.
        print('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'genome_input_ref' not in params:
            raise ValueError('Parameter genome_input_ref is not set in input arguments')
        genome_input_ref = params['genome_input_ref']

        data_file_cli = DataFileUtil(self.callback_url)
        genome = data_file_cli.get_objects({'object_refs': [genome_input_ref]})
        genome_data = genome['data'][0]['data']

        print (list(genome_data.keys()))

        report_format = params['report_format']
        string = ''
        if report_format == 'tab':
            cf = CreateFeatureLists(self.config)
            string = cf.delimitedTable(genome_data, 'tab', 'features')
            report_path = os.path.join(self.scratch, 'genome_report.tsv')
        elif report_format == 'csv':
            cf = CreateFeatureLists(self.config)
            string = cf.delimitedTable(genome_data, 'csv', 'features')
            report_path = os.path.join(self.scratch, 'genome_report.csv')
        elif report_format == 'gff':
            cf = CreateFeatureLists(self.config)
            string = cf.gff3(genome_data, 'features')
            report_path = os.path.join(self.scratch, 'genome_report.gff')
        elif report_format == 'fasta':
            cf = CreateFasta(self.config)
            string = cf.create_Fasta_from_features(genome_data['features'])
            report_path = os.path.join(self.scratch, 'genome_report.faa')
        elif report_format == 'mRNA':
            cf = CreateFasta(self.config)
            string = cf.create_Fasta_from_mRNA(genome_data['features'])
            report_path = os.path.join(self.scratch, 'genome_report.fna')
        elif report_format == 'DNA':
#            string += "\nFASTA of the DNA Sequences\n"
            report_path = os.path.join(self.scratch, 'genome_dna_report.fna')
            if 'assembly_ref' in genome_data:
                assembly_input_ref = genome_data['assembly_ref']
                string += self.get_assembly_sequence(assembly_input_ref)
            else:
                string += 'Did not find the Assembly Reference\n'

        else:
            raise ValueError('Invalid report option.' + str(report_format))


        report_txt = open(report_path, "w")
        report_txt.write(string)
        report_txt.close()
        report_path = os.path.join(self.scratch, 'text_report.html')
        report_txt = open(report_path, "w")
        report_txt.write("<pre>" + string + "</pre>")
        report_txt.close()

#        print string
        cr = Report_creator(self.config)
        reported_output = cr.create_report(token, params['workspace_name'],
                                    string, self.scratch)

        output = {'report_name': reported_output['name'],
                  'report_ref': reported_output['ref']}

        print('returning: ' + pformat(output))
        #END genome_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method genome_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def genomeset_report(self, ctx, params):
        """
        :param params: instance of type "GenomeSetReportParams" -> structure:
           parameter "genomeset_input_ref" of type "genomeset_ref", parameter
           "workspace_name" of String, parameter "report_format" of String
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN genomeset_report
        token = ctx['token']

        # Print statements to stdout/stderr are captured and available as the App log
        print('Starting Genome Set Report Function. Params=')
        pprint(params)

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.
#        print('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'genomeset_input_ref' not in params:
            raise ValueError('Parameter genomeset_input_ref is not set in input arguments')
        genomeset_input_ref = params['genomeset_input_ref']

        data_file_cli = DataFileUtil(self.callback_url)
        genomeset = data_file_cli.get_objects({'object_refs': [genomeset_input_ref]})
        genome_name = genomeset['data'][0]['info'][1]
        genomeset_data = genomeset['data'][0]['data']

#        print genomeset_data.keys()

        report_format = params['report_format']
        string = ''
        if report_format == 'tab':
            gsr = CreateMultiGenomeReport(self.config)
            string = gsr.readGenomeSet(genome_name, genomeset_data, 'tab')
            report_path = os.path.join(self.scratch, 'genomeset_report.tsv')
        elif report_format == 'csv':
            gsr = CreateMultiGenomeReport(self.config)
            string = gsr.readGenomeSet(genome_name, genomeset_data, 'csv')
            report_path = os.path.join(self.scratch, 'genomeset_report.csv')
        elif report_format == 'list':
            gsr = CreateMultiGenomeReport(self.config)
            string = gsr.readGenomeSet(genome_name, genomeset_data, 'list')
            report_path = os.path.join(self.scratch, 'genomeset_report.txt')
        elif report_format == 'meta':
            gsr = CreateMultiGenomeReport(self.config)
            string = gsr.getGenomeSetMeta(genomeset['data'][0])
            report_path = os.path.join(self.scratch, 'genomeset_report.txt')
        elif report_format == 'fasta':
            gsr = CreateMultiGenomeReport(self.config)
            assembly_list = gsr.getAssemblyRef(genomeset['data'][0])
            string = ''
            for assembly in assembly_list:
                 assembly_ref, sci_name = assembly.split(':')
                 dna = self.get_assembly_sequence(assembly_ref)
                 report_path = os.path.join(self.scratch, 'G'+assembly_ref.replace('/', '_')+'.fna')
                 report_txt = open(report_path, "w")
                 report_txt.write(dna)
                 report_txt.close()
                 string += assembly_ref+'-'+sci_name+"\n"
            report_path = os.path.join(self.scratch, 'genomeset_report.txt')
        else:
            raise ValueError('Invalid report option.' + str(report_format))

        report_txt = open(report_path, "w")
        report_txt.write(string)
        report_txt.close()
        report_path = os.path.join(self.scratch, 'text_report.html')
        report_txt = open(report_path, "w")
        report_txt.write("<pre>" + string + "</pre>")
        report_txt.close()

#        print string
        cr = Report_creator(self.config)
        reported_output = cr.create_report(token, params['workspace_name'],
                                           string, self.scratch)

        output = {'report_name': reported_output['name'],
                  'report_ref': reported_output['ref']}

#        print('returning: ' + pformat(output))
        #END genomeset_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method genomeset_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def domain_report(self, ctx, params):
        """
        :param params: instance of type "DomainReportParams" -> structure:
           parameter "domain_annotation_input_ref" of type "domain_ref",
           parameter "evalue_cutoff" of Double, parameter "workspace_name" of
           String, parameter "report_format" of String
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN domain_report
        token = ctx['token']

        # Print statements to stdout/stderr are captured and available as the App log
        print('Starting Domain Annotation Report Function. Params=')
        pprint(params)

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.
        print('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'domain_annotation_input_ref' not in params:
            raise ValueError('Parameter domain_annotation_input_ref is not set in input arguments')
        domain_annotation_input_ref = params['domain_annotation_input_ref']

        data_file_cli = DataFileUtil(self.callback_url)
        domain_anno = data_file_cli.get_objects({'object_refs': [domain_annotation_input_ref]})
        domain_data = domain_anno['data'][0]['data']
#        print (list(domain_data.keys()))

        evalue_cutoff = float(params['evalue_cutoff'])
        report_format = params['report_format']
        string1 = ''
        string2 = ''
        if report_format == 'tab':
            cf = CreateFeatureLists(self.config)
            string1 = cf.readDomainAnnList(domain_data, 'tab', evalue_cutoff)
            string2 = cf.readDomainAnnCount(domain_data, 'tab', evalue_cutoff)
            report_path1 = os.path.join(self.scratch, 'domain_annotation_list.tsv')
            report_path2 = os.path.join(self.scratch, 'domain_annotation_count.tsv')
        elif report_format == 'csv':
            cf = CreateFeatureLists(self.config)
            string1 = cf.readDomainAnnList(domain_data, 'csv', evalue_cutoff)
            string2 = cf.readDomainAnnCount(domain_data, 'csv', evalue_cutoff)
            report_path1 = os.path.join(self.scratch, 'domain_annotation_list.csv')
            report_path2 = os.path.join(self.scratch, 'domain_annotation_count.csv')
        else:
            raise ValueError('Invalid report option.' + str(report_format))

        report_txt = open(report_path1, "w")
        report_txt.write(string1)
        report_txt.close()
        report_txt = open(report_path2, "w")
        report_txt.write(string2)
        report_txt.close()

        report_path = os.path.join(self.scratch, 'text_report.html')
        report_txt = open(report_path, "w")
        report_txt.write("<pre>" + string2 + "</pre>")
        report_txt.write("<pre>" + string1 + "</pre>")
        report_txt.close()

        #        print string
        cr = Report_creator(self.config)

        reported_output = cr.create_report(token, params['workspace_name'],
                                           string2, self.scratch)

        output = {'report_name': reported_output['name'],
                  'report_ref': reported_output['ref']}

        print('returning: ' + pformat(output))
        #END domain_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method domain_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def tree_report(self, ctx, params):
        """
        :param params: instance of type "TreeReportParams" -> structure:
           parameter "tree_input_ref" of type "tree_ref", parameter
           "workspace_name" of String, parameter "report_format" of String
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN tree_report
        #END tree_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method tree_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def featseq_report(self, ctx, params):
        """
        :param params: instance of type "FeatSeqReportParams" -> structure:
           parameter "feature_sequence_input_ref" of type "featseq_ref",
           parameter "workspace_name" of String, parameter "report_format" of
           String
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN featseq_report
        token = ctx['token']

        # Print statements to stdout/stderr are captured and available as the App log
        print('Starting FeatureSeq/SequenceSet Report Function. Params=')
        pprint(params)

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.
        print('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'feature_sequence_input_ref' not in params:
            raise ValueError('Parameter feature_sequence_input_ref is not set in input arguments')
        feature_sequence_input_ref = params['feature_sequence_input_ref']

        data_file_cli = DataFileUtil(self.callback_url)
        setseq = data_file_cli.get_objects({'object_refs': [feature_sequence_input_ref]})
        setseq_data = setseq['data'][0]['data']

        #print (list(setseq_data.keys()))

        report_format = params['report_format']
        string1 = ''
        if report_format == 'tab':
            cf = CreateFeatureLists(self.config)
            string1 = cf.readFeatSeq(setseq_data, 'tab')
            report_path1 = os.path.join(self.scratch, 'sequence_set_list.tsv')
        elif report_format == 'csv':
            cf = CreateFeatureLists(self.config)
            string1 = cf.readFeatSeq(setseq_data, 'csv')
            report_path1 = os.path.join(self.scratch, 'sequence_set_list.csv')
        else:
            raise ValueError('Invalid report option.' + str(report_format))

        report_txt = open(report_path1, "w")
        report_txt.write(string1)
        report_txt.close()

        report_path = os.path.join(self.scratch, 'text_report.html')
        report_txt = open(report_path, "w")
        report_txt.write("<pre>" + string1 + "</pre>")
        report_txt.close()

        #        print string
        cr = Report_creator(self.config)

        reported_output = cr.create_report(token, params['workspace_name'],
                                           string1, self.scratch)

        output = {'report_name': reported_output['name'],
                  'report_ref': reported_output['ref']}

        print('returning: ' + pformat(output))
        #END featseq_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method featseq_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]

    def protcomp_report(self, ctx, params):
        """
        :param params: instance of type "ProtCompReportParams" -> structure:
           parameter "protcomp_input_ref" of type "protcomp_ref", parameter
           "workspace_name" of String, parameter "report_format" of String
        :returns: instance of type "ReportResults" (Here is the definition of
           the output of the function.  The output can be used by other SDK
           modules which call your code, or the output visualizations in the
           Narrative.  'report_name' and 'report_ref' are special output
           fields- if defined, the Narrative can automatically render your
           Report.) -> structure: parameter "report_name" of String,
           parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN protcomp_report
        token = ctx['token']

        # Print statements to stdout/stderr are captured and available as the App log
        print('Starting ProteomeComparison Report. Params=')
        pprint(params)

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.
        print('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'protcomp_input_ref' not in params:
            raise ValueError('Parameter protcomp_input_ref is not set in input arguments')
        protcomp_input_ref = params['protcomp_input_ref']

        data_file_cli = DataFileUtil(self.callback_url)
        protcomp = data_file_cli.get_objects({'object_refs': [protcomp_input_ref]})
        protcomp_data = protcomp['data'][0]['data']

        #print ("DEBUG KEYS: ", list(protcomp_data.keys()))

        report_format = params['report_format']
        string1 = ''
        if report_format == 'tab':
            cf = CreateFeatureLists(self.config)
            string1 = cf.readProtComp(protcomp_data, 'tab')
            report_path1 = os.path.join(self.scratch, 'protcomp_list.tsv')
        elif report_format == 'csv':
            cf = CreateFeatureLists(self.config)
            string1 = cf.readProtComp(protcomp_data, 'csv')
            report_path1 = os.path.join(self.scratch, 'protcomp_list.csv')
        else:
            raise ValueError('Invalid report option.' + str(report_format))

        report_txt = open(report_path1, "w")
        report_txt.write(string1)
        report_txt.close()

        report_path = os.path.join(self.scratch, 'text_report.html')
        report_txt = open(report_path, "w")
        report_txt.write("<pre>" + string1 + "</pre>")
        report_txt.close()

        #        print string
        cr = Report_creator(self.config)

        reported_output = cr.create_report(token, params['workspace_name'],
                                           string1, self.scratch)

        output = {'report_name': reported_output['name'],
                  'report_ref': reported_output['ref']}

        #END protcomp_report

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method protcomp_report return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
