import os
from pathlib import Path 
import csv
from typing import Dict
from postAnalysisUtils import exportLLMPTestResults, analyzeTestResults, extendTestResultsWithExternalSuite

def postMortem1(datasetFile:str, dirInputJsons:str,  additionalTestsFile:str, dirToPutOutputFiles:str):
    print("** ==== Start post-mortem-1")
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

    print("** Analyzing test-results ...")
    k = 0
    summaries = []
    for file in Path(dirToPutOutputFiles).iterdir():  
        baseName = os.path.basename(file)
        if file.is_file() and file.suffix == ".json" and baseName.startswith("testResults_") :  
            baseName = os.path.basename(file)
            baseName = os.path.splitext(baseName)[0]
            print("   > " + baseName)
            A = analyzeTestResults(file,dirToPutOutputFiles)
            summaries.append(A)
            k += 1
    print(f"** #testResults-files proecessed: {k}" )
    print("** Exporting summaries to csv...")
    summaries2csv(summaries,"pre",dirToPutOutputFiles)
    summaries2csv(summaries,"post",dirToPutOutputFiles)
    print(f"** ==== done")

def summaries2csv(summaries,cond,dirToPutOutputFile):
    table = []
    for Z in summaries: # of LLM-Z
        baseName = Z[0]
        if cond=="pre":
            data = Z[1] # pre-cond data
        else:
            data = Z[2] # post-cond data
        data2 = { "LLM" : baseName }
        for X in data:
            suiteName = X["testsuite-name"]
            data2[suiteName+"_avrg_accepted@1"] = X["avrg_accepted@1"]
            data2[suiteName+"_avrg_weaklyaccepted@1"] = X["avrg_weaklyaccepted@1"]
            data2[suiteName+"_acceptedAtLeastOne_percentage"] = X["acceptedAtLeastOne_percentage"]
            data2[suiteName+"_weaklyacceptedAtLeastOne_percentage"] = X["weaklyacceptedAtLeastOne_percentage"]
            data2[suiteName+"_averageTCsPassRate"]= X["averageTCsPassRate"]
        table.append(data2)
        
    if len(table) == 0: return

    csvfile = os.path.join(dirToPutOutputFile, f"{cond}cond-summaries.csv")
    with open(csvfile, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(table[0].keys())
        for row in table:
            writer.writerow(row.values())  




# example use:
if __name__ == '__main__':
   ROOT = os.path.dirname(os.path.abspath(__file__))
   dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "HEx-compact.json")
   additionalTests = os.path.join(ROOT, "results","coba-postmortem","pynguin_hex_generatedTests.json")
   idir = os.path.join(ROOT, "results","coba-postmortem","fromLLMs")
   odir = os.path.join(ROOT, "results","coba-postmortem","postmortem")
   postMortem1(dataset,idir,additionalTests,odir)