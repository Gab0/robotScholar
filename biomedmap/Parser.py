#!/bin/python
"""

This application downloads and parser PMID entries
to a format recognizable by INDRA;

"""
import re
import time

from multiprocessing.pool import Pool, MaybeEncodingError
import json
import sys
import os
import datetime
import collections
import contextlib
import argparse
import resource
import psutil

from Bio import Entrez

from indra.sources import trips
from indra.assemblers.pysb import PysbAssembler

from indra.sources import reach
import indra.literature.pmc_client as pmc_client

from indra.ontology.bio.ontology import BioOntology

import xmltodict

# FIXME: NOT good practice.
Entrez.email = "robot@scholar.com"

# MAKE BIO ONTOLOGY INITIALIZE GLOBALLY!
d = BioOntology()


class Logger():
    """

    Handles the log logic;

    """

    def __init__(self, fpath):
        self.fpath = fpath

    def __call__(self, message):
        with open(self.fpath, 'a+') as f:
            timestamp = self.get_timestamp()
            f.write(f"{timestamp} {message}\n")

    @staticmethod
    def get_timestamp():
        return datetime.datetime.now().strftime("[%H:%M]")


def interpreteProcessor(processor, Article, filePaths, PMID):
    with open(filePaths["main"], 'w') as out:
        Output = processor.tree.data
        Output["Title"] = Article["Title"]

        print("Saving data for:\n %s\n" % Output["Title"])
        json.dump(Output, out, indent=2)


def processReach(PMID, options):
    PMIDcode = re.sub("PMC", "", PMID)

    # Build file output paths;
    baseFilePath = os.path.join(options.outputDirectory, PMID)

    filePaths = {
        "main": "%s.json" % baseFilePath,
        "statements": "%s-statements.json" % baseFilePath
    }

    if os.path.isfile(filePaths["main"]):
        print("Skipping...")
        return True

    print("Original PMID: %s\n\tSearching %s...\n" % (PMID, PMIDcode))

    stTime = time.time()
    processor = None

    Article = download_nxml(PMID)

    if Article is not None:
        try:
            fname = "%s.nxml" % PMID if options.KeepNXML else "buffer.nxml"

            processor = reach.process_nxml_str(Article['Content'],
                                               output_fname=fname)
        except Exception as e:
            print("Failure on reach processor.")
            print(e)
            return False

        print("Took %.2f seconds to process %s." % (time.time() - stTime, PMID))

    if not os.path.isdir(options.outputDirectory):
        os.mkdir(options.outputDirectory)

    if processor is not None:
        interpreteProcessor(processor, Article, filePaths, PMID)
        return True

    return False


def fetchDictionaryKey(Dictionary, keys):
    for k in keys:
        if k in Dictionary.keys():
            Dictionary = Dictionary[k]
        else:
            print("%s not found." % k)
            print(Dictionary.keys())
            json.dump(Dictionary,
                      fp=open("article_content.json", 'w'),
                      indent=2)

            return None

    return Dictionary


def entrez_xml(PMID):
    data = list(Entrez.efetch(db="pmc", id=PMID))
    data = [d.decode('utf-8') for d in data]
    data = "".join(data)
    if "<body>" in data:
        return data

    print(data)
    return None


def download_nxml(PMID):
    articleGetters = [
        # pmc_client.get_xml,
        entrez_xml
    ]

    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull):
            with contextlib.redirect_stderr(devnull):
                Article = [
                    articleGetter(PMID)
                    for articleGetter in articleGetters
                ]

    if len(Article) > 1:
        if "<body>" in Article[1] and not Article[0]:
            print("Data:")
            print(Article[1])
            print("Anomaly")
            open("scholar_log.txt", 'a+').write("ANOMALY %s" % PMID)
            Article = Article[1]
    else:
        Article = Article[0]

    if None in [Article]:
        print("Cannot fetch article %s!\n\n" % PMID)
        return None

    ArticleData = xmltodict.parse(Article)
    TitlePath = [
        'pmc-articleset',
        'article',
        'front',
        'article-meta',
        'title-group',
        'article-title'
    ]

    _LegacyTitlePath = [
        'OAI-PMH',
        'GetRecord',
        'record',
        'metadata',
        'article',
        'front',
        'article-meta',
        'title-group',
        'article-title'
    ]

    Title = fetchDictionaryKey(ArticleData, TitlePath)

    if Title is None:
        print("Cannot find article Title for %s" % PMID)
        return None

    if isinstance(Title, collections.OrderedDict):
        Title = Title['#text']

    return {
        "Title": Title,
        "Content": Article
    }


def processText(Text):
    pa = PysbAssembler()
    # Process a natural language description of a mechanism
    trips_processor = trips.process_text(Text)

    # Collect extracted mechanisms in PysbAssembler
    pa.add_statements(trips_processor.statements)

    # Assemble the model
    model = pa.make_model(policies='two_step')
    return model


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [
        alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
        for i in range(wanted_parts)
    ]


def parse_arguments(parser=argparse.ArgumentParser()):
    parser.add_argument("-p", dest="pmcidList")
    parser.add_argument("-d", dest="outputDirectory")
    parser.add_argument("-k", dest="KeepNXML", action="store_true")
    parser.add_argument("-f", dest="FromID")
    parser.add_argument('-n', dest="maxProcs", type=int, default=3)

    return parser


def post_process_arguments(options):
    if options.outputDirectory == options.pmcidList:
        print("Output directory path is the same as PMCID list path.")
        sys.exit(1)
    if not options.pmcidList:
        print("No input PMCid file list specified.")
        sys.exit(1)

    if not options.outputDirectory:
        options.outputDirectory =\
            os.path.splitext(os.path.basename(options.pmcidList))[0]
        print("Defaulting output directory to %s" % options.outputDirectory)

    return options


def readPMCIDList(options):
    ProcessArgumentBatch = []
    Enabled = not options.FromID
    f = open(options.pmcidList)
    for line in f:
        if line:
            line = line.strip("\n")
            if not Enabled:
                if line in options.FromID:
                    Enabled = True
            if Enabled:
                ProcessArgumentBatch.append((line, options))

    return ProcessArgumentBatch


def main():
    options = parse_arguments().parse_args()
    execute(options)


def execute(options):
    options = post_process_arguments(options)

    procpool = Pool(processes=options.maxProcs)

    ProcessArgumentBatch = readPMCIDList(options)

    logger = Logger(f"PARSE_{options.pmcidList}.log")

    print("Batches:")
    print(len(ProcessArgumentBatch))
    print(ProcessArgumentBatch)

    WantedParts = max(2, len(ProcessArgumentBatch) // 8)
    ProcessArgumentBatch = split_list(ProcessArgumentBatch,
                                      wanted_parts=WantedParts)
    AllResults = []

    for Batch in ProcessArgumentBatch:
        print("Processing batch #1")
        results = procpool.starmap_async(processReach, Batch)

        try:
            output_results = results.get()
            AllResults += output_results
        except MaybeEncodingError:
            print("Failure.")

        # Manage RAM usage;
        AskMemoryUsage()
        Usage, Total = get_memory_usage()
        logger(f"Memory usage: {b_to_mb(Usage)}Mb of {b_to_mb(Total)}Mb")

    totalN = sum([len(Batch) for Batch in ProcessArgumentBatch])
    SuccessRate = (100 * sum(AllResults) / totalN)
    print("\nSuccess Rate is %.2f%% at %s." % (
        SuccessRate,
        options.outputDirectory))


def b_to_mb(b):
    return b / (1 << 20)


def get_memory_usage():
    Usage = resource.getrusage(
        resource.RUSAGE_CHILDREN).ru_maxrss +\
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    Total = psutil.virtual_memory().total

    return (Usage, Total)


def AskMemoryUsage():
    Usage, Total = get_memory_usage()
    print("Using %i kb" % Usage)
    print("%.2f available" % Total)
    if Usage > 1000000:
        input("Allow?")


if __name__ == "__main__":
    main()
