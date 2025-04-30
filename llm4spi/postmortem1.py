import os
from pathlib import Path 
import csv
from typing import Dict
from postAnalysisUtils import exportLLMPTestResults, analyzeTestResults, extendTestResultsWithExternalSuite

def collectTestResults(datasetFile:str, dirInputJsons:str,  additionalTestsFile:str, dirToPutOutputFiles:str):
    '''
    Collect test results from the original LLMs evaluation into separate test-result files.
    If additional-tests are given, they will be run and the results added into the output-files.

    Test-results are put in files startwith testResult_ per json-file of the orginal LLM evaluation.
    If additional tests are give, files starting with extendedtestResults_ are generated.
    They contain test-results in the corresponding testResults_ file, plus the results of
    additional tests.

    * datasetFile: the json-file that describes the data/problem-set.
    * dirInputJsons: directory containing tje json-outputs of the orginal LLMs evaluation on the dataset.
    * additionalTestsFile: if specified (not None), this is a file containing additional tests for each problem in the dataset.
    * dirToPutOutputFiles: directory where to put the output files of this function.
    '''
    print("** ==== Start collecting test results.")
    print("** Collecting test-results, reorganizing the data, saving them to testResults-files ...")
    k = 0
    preconds_summaries = []
    postcond_summaries = []
    for file in Path(dirInputJsons).iterdir():  
        if file.is_file() and file.suffix == ".json" : 
            baseName = os.path.basename(file)
            baseName = os.path.splitext(baseName)[0]
            print("   > " + baseName)
            exportLLMPTestResults(datasetFile,file,dirToPutOutputFiles)
            k += 1
    print(f"** #input-files proecessed: {k}" )

    if additionalTestsFile != None:
        print("** Adding external tests ...")
        for file in Path(dirInputJsons).iterdir():  
            if file.is_file() and file.suffix == ".json" : 
                baseName = os.path.basename(file)
                baseName = os.path.splitext(baseName)[0]
                baseTestResultsFile = os.path.join(dirToPutOutputFiles, "testResults_" + baseName + ".json")
                extendTestResultsWithExternalSuite(datasetFile,
                                          file,
                                          baseTestResultsFile,
                                          "pynguin",
                                          additionalTestsFile,
                                          dirToPutOutputFiles)
        print(f"** adding external tests done.")
    print(f"** ==== Done.")


def summaries2csv(summaries,cond,dirToPutOutputFile):
    table = []
    for Z in summaries: # of LLM-Z
        baseName = Z[0]
        if cond=="pre":
            data = Z[1] # pre-cond data
        elif cond=="post":
            data = Z[2] # post-cond data
        else:  # cond is "both"
            data = Z[3]
        data2 = { "LLM" : baseName }
        for X in data:
            suiteName = X["testsuite-name"]
            data2[suiteName+"_avrg_accepted@1"] = X["avrg_accepted@1"]
            data2[suiteName+"_avrg_weaklyaccepted@1"] = X["avrg_weaklyaccepted@1"]
            data2[suiteName+"_acceptedAtLeastOne_percentage"] = X["acceptedAtLeastOne_percentage"]
            data2[suiteName+"_weaklyacceptedAtLeastOne_percentage"] = X["weaklyacceptedAtLeastOne_percentage"]
            data2[suiteName+"_averageTCsPassRate"]= X["averageTCsPassRate"]
            #data2[suiteName+"_totNumOftests"]= X["tot #tests"]
        table.append(data2)
        
    if len(table) == 0: return

    csvfile = os.path.join(dirToPutOutputFile, f"{cond}cond-summaries.csv")
    with open(csvfile, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(table[0].keys())
        for row in table:
            writer.writerow(row.values())  

def postmortem_analysis1(dirOfTestResultFiles:str, withExternalResults:bool = False):
    print(f"** ==== Start post-mortem analysis 1 {dirOfTestResultFiles}")
    print("** Analyzing test-results ...")
    k = 0
    summaries = []
    for file in Path(dirOfTestResultFiles).iterdir():  
        baseName = os.path.basename(file)
        if file.is_file() and file.suffix == ".json" :  
            if (   (withExternalResults==False and baseName.startswith("testResults_"))
                or (withExternalResults==True  and baseName.startswith("extendedtestResults_"))):
               baseName = os.path.basename(file)
               baseName = os.path.splitext(baseName)[0]
               print("   > " + baseName)
               A = analyzeTestResults(file,dirOfTestResultFiles)
               summaries.append(A)
               k += 1
    print(f"** #testResults-files proecessed: {k}" )
    print("** Exporting summaries to csv...")
    summaries2csv(summaries,"pre",dirOfTestResultFiles)
    summaries2csv(summaries,"post",dirOfTestResultFiles)
    summaries2csv(summaries,"both",dirOfTestResultFiles)
    print(f"** ==== Done")


# example use:
if __name__ == '__main__':
   ROOT = os.path.dirname(os.path.abspath(__file__))
   dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "HEx-compact.json")
   additionalTests = os.path.join(ROOT, "results","coba-postmortem","pynguin_hex_generatedTests.json")
   idir = os.path.join(ROOT, "results","coba-postmortem","fromLLMs")
   odir = os.path.join(ROOT, "results","coba-postmortem","postmortem")
   #collectTestResults(dataset,idir,additionalTests,odir)
   #print(f"### {odir}")
   postmortem_analysis1(odir,True)