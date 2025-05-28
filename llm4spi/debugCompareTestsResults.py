import os
from pathlib import Path 
import csv
from typing import Dict
from data import read_problems, write_json
from basicEvaluate import extractTests
import json

def runTestsAndSave(datasetFile:str, additionalTestsFile:str, dirToPutOutputFiles:str):
    '''
    Run the tests of a dataset, and save the (test,result) pairs in a json-file. You can
    also specify an additional/external test suite; these will then be run as well.

    * datasetFile: the json-file that describes the data/problem-set.
    * additionalTestsFile: if specified (not None), this is a file containing additional tests for each problem in the dataset.
    * dirToPutOutputFiles: directory where to put the output files of this function.
    '''

    # get the tests provided by the dataset:
    def getTestSuite(cond,task):
        testSuites = extractTests(cond,task)
        # well... let's just merge them into one suite:
        return testSuites["suite_Base0"] + testSuites["suite_Base1"] + testSuites["suite_Validation"]

    # for collecting the test-results of a sigle task/problem:    
    def getTestResults(cond:str, task:Dict, extraTestSuite:Dict):
        tId = task["task_id"]

        # we first handle the case when the task pre- or post-condition
        # does not exists:
        if not (f"{cond}_condition_solution" in task) : 
            return None
        solution_function = task[f"{cond}_condition_solution"]
        if solution_function==None or solution_function=="":
            return None
    
        # executing the solution-function DEF; not expecting it to fail
        try:
            exec(solution_function,globals())
        except:
            print(">>>>>> Ouch. The def of the solution function CRASHED!")
            print(solution_function)
            return None

        testSuites = getTestSuite(cond,task)
        
        # executing the test-cases on the solution-function, also not expecting these
        # to fail:
        print(f"  Running original test suites {tId}-{cond} #={len(testSuites)}")
        results = [ { "suite"  : "original",
                      "test"   : f"{test_case}", 
                      "result" : eval(f"check_{cond}_solution_{tId}(*test_case)") }
                      for test_case in testSuites]
        
        if extraTestSuite != None:
            extraS = extraTestSuite[tId]
            print(f"  Running extra test suites {tId}-{cond} #={len(extraS)}")
            results2 = [ { "suite"  : "extra",
                      "test"   : f"{test_case}", 
                      "result" : eval(f"check_{cond}_solution_{tId}(*test_case)") }
                      for test_case in extraS]
            
            results = results + results2
             
        return results
    
    def getTestSuiteEmbeddedInStr(str):
        if str == []: 
                return []
        return eval(str)
    
    externalTestsuite_pre = None
    externalTestsuite_post = None
    if additionalTestsFile != None:
        print("** Reading external tests ...")
        with open(additionalTestsFile, "r") as fp:
            externalTestsuite = json.load(fp)
            

            # we'll just merge the positive and negative tests; we will re-check the polarity later and
            # re-assign the polarity accordingly:
            externalTestsuite_pre  = { task["problemId"] : getTestSuiteEmbeddedInStr(task[f"positive_pre_tests"]) + getTestSuiteEmbeddedInStr(task[f"negative_pre_tests"])
                                     for task in externalTestsuite}
            externalTestsuite_post = { task["problemId"] : getTestSuiteEmbeddedInStr(task[f"positive_post_tests"]) + getTestSuiteEmbeddedInStr(task[f"negative_post_tests"])
                                     for task in externalTestsuite}
        
      

    tasks = read_problems(datasetFile)
    print("** ==== Running tests...")
    allresults = []
    for tId in tasks:
        task = tasks[tId]
        resultsPre = getTestResults("pre",task,externalTestsuite_pre)
        resultsPost = getTestResults("post",task,externalTestsuite_post)
        allresults.append({"task_id" : tId, "pre" : resultsPre, "post" : resultsPost})
    print("** ==== Saving the results")

    outputBaseName = os.path.basename(datasetFile)
    outputBaseName = os.path.splitext(outputBaseName)[0]
    testResultsFile = "DEBUG_testResults_" + outputBaseName + ".json"
    testResultsFile = os.path.join(dirToPutOutputFiles, testResultsFile)
    write_json(testResultsFile, allresults)

def debugCompareTestResults(testsResultsFile1:str, testsResultsFile2:str):
    '''
    Compare if two test-results are identical.
    '''
    with open(testsResultsFile1, "r") as f1:
        results1 = json.load(f1)
    with open(testsResultsFile2, "r") as f2:
        results2 = json.load(f2)
    same = results1 == results2
    if same : return same
    # ok so there are differences.. find and print:
    for (T1a,T1b) in zip (results1,results2) :
        if T1a == T1b : continue
        tId = T1a["task_id"]
        print(f"** Found differing test-result {tId}")
        preA = T1a["pre"]
        preB = T1b["pre"]
        if preA != preB :
            for (ta,tb) in zip(preA,preB):
                if ta != tb:
                    print(f"   test-1: {ta}")
                    print(f"   test-2: {tb}")
        postA = T1a["post"]
        postB = T1b["post"]
        if postA != postB :
            for (ta,tb) in zip(postA,postB):
                if ta != tb:
                    print(f">>> test-1: {ta}")
                    print(f"    test-2: {tb}")
    return same
    
# example use:
if __name__ == '__main__':
   ROOT = os.path.dirname(os.path.abspath(__file__))
   dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "HEx-compact.json")
   additionalTests = os.path.join(ROOT, "results","coba-postmortem","pynguin_hex_generatedTests.json")
   odir = os.path.join(ROOT, "results")
   runTestsAndSave(dataset,additionalTests,odir)
   f1 = os.path.join(ROOT, "results","DEBUG_testResults_HEx-compact-2025-may-22.json")
   f2 = os.path.join(ROOT, "results","DEBUG_testResults_HEx-compact.json")
   same = debugCompareTestResults(f1,f2)
   print(f"comparing {f1} vs {f2}; identical:{same}")





   