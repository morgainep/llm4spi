import json
import os.path
import statistics
from func_timeout import func_timeout, FunctionTimedOut
from typing import Dict

from data import read_problems, write_json
import myconfig
from basicEvaluate import extractTests, compare_results

DEBUG = False

def exportOutLLMProposals(datasetFile:str, outputjsonFile:str, dirToPutGeneratedPy:str):
    """
    Export all proposed pre-/post-conditions produced by an LLM to actual Python functions.
    The parameter outputjson is the name, with path, of the json-file containing the json
    output of a benchmarking run.

    The parameter datasetFile is the json file containing the dataset of problems to which
    the output belongs to.

    All proposals from LLM will be exported as Python functions, put in a single
    Python-file, with the same base-name as outputjson, But it will be placed in the
    dir specified by dirToPutGeneratedPy.
    """
    problems = read_problems(datasetFile)
    outputBaseName = os.path.basename(outputjson)
    outputBaseName = os.path.splitext(outputBaseName)[0]
    with open(outputjsonFile, "r") as fp:
        results = json.load(fp)

    pyfname = "proposals_" + outputBaseName + ".py"
    pyfname = os.path.join(dirToPutGeneratedPy, pyfname)

    with open(pyfname, "w") as fpy:

        def writeProposals(Tid:str, condTy:str, completions:list[str]):
            k = 0
            for body in completions:
                header0 = problems[Tid][f"{condTy}_condition_incomplete"]
                params = header0[header0.find("("):]
                funcHeader = f"def check_{condTy}_{Tid}_{k}" + params
                if body == None or body == "":
                    body = "   raise Exception(\"No proposal can be extracted.\")\n"
                func = funcHeader + "\n" + body + "\n\n"
                fpy.write(func)
                k = k+1

        fpy.write("#\n# Generated file\n#\n\n")

        for R in results:
            Tid = R["task_id"]
            fpy.write("# ----------------------\n")
            fpy.write(f"# Proposals for {Tid}\n")
            fpy.write("# ----------------------\n\n")
            
            T = problems[Tid]
            if "pre_condition_solution" in T:
                completions = R["pre_condition_completions"]
                writeProposals(Tid,"pre",completions)
            if "post_condition_solution" in T:
                completions = R["post_condition_completions"]
                writeProposals(Tid,"post",completions)

def exportLLMPTestResults(datasetFile:str, outputjsonFile:str, dirToPutOutputFile:str):
    """
    This takes the evaluation output file from xxx4spi script (e.g. openai4spi),
    and collects and reorganizes the results of running the tests-cases, 
    and puts them in an output file.

    The input json-data is a list, where each element represent a task/problem T.
    It contains, among others, LLM's candidates for pre/post-conditions in the
    problem T. It also contains the results on running the test-cases in T on 
    each of these candidates. This function will extract these test-results 
    and re-arrange them so that for e.g. T's post-cond, we construct a list
    of results. Each item nr-k in this list is essentially a tuple (actually, a 
    dictionary) (tag,tc,r,e) were tc is the test-case (values), r is the result
    (true/false/None) of running this tc on post-cond-candidate k, e is the 
    expected result (true/false) of running tc on the solution-post-cond.
   
    The tag is a name of the test-suite to which tc belongs to.

    The resulting lists of results are written to a new json file, named testResultsxxx.json.
    """
    problems = read_problems(datasetFile)

    outputBaseName = os.path.basename(outputjsonFile)
    outputBaseName = os.path.splitext(outputBaseName)[0]
    with open(outputjsonFile, "r") as fp:
        baseEvaluationResults = json.load(fp)

    def putTogetherTestResults(suiteName,tests,results,expectedResults):
        return [ { "suite" : suiteName,
                   "test" : f"{tc}",
                   "result" : r,
                   "expected" : expected } 
                   for (tc,r,expected) in zip(tests,results,expectedResults) ]

    # for collecting the test-results of a sigle task/problem:    
    def getTestResultsOfSolution(cond:str, task:Dict):
        tId = task["task_id"]
        tests = extractTests(cond,problems[tId])
        expectedResults = task[f"{cond}_condition_reference_TestResults"]
        expectedResults_base0 = expectedResults["base0"]
        expectedResults_base1 = expectedResults["base1"]
        expectedResults_validationSuite = expectedResults["validationSuite"]
        numberOfCandidates = len(task[f"{cond}_condition_completions"])
        all_results = []
        for k in range(0, numberOfCandidates) :
            results = task[f"{cond}_condition_candidates_TestResults"][k]
            if results["def-loaded"] == "success" :
                results_base0 = results["base0"]
                results_base1 = results["base1"]
                results_validationSuite = results["validationSuite"]
            else:
                results_base0 = [None] * len(expectedResults_base0)
                results_base1 = [None] * len(expectedResults_base1)
                results_validationSuite = [None] * len(expectedResults_validationSuite)

            z0 = putTogetherTestResults("human-positive",tests["suite_Base0"],results_base0,expectedResults_base0)
            z1 = putTogetherTestResults("human-negative",tests["suite_Base1"],results_base1,expectedResults_base1)
            z2 = putTogetherTestResults("human-validation",tests["suite_Validation"],results_validationSuite,expectedResults_validationSuite)
            all_results.append(z0 + z1 + z2)
            
        return all_results

    # collect the test-results for all tasks, put them in this list:
    allall_results = [ {
          "task_id" : T["task_id"],
          "pre_condition" : None if T["pre_condition_prompt"] == None else getTestResultsOfSolution("pre",T),
          "post_condition" : None if T["post_condition_prompt"] == None else getTestResultsOfSolution("post",T)
        }
        for T in baseEvaluationResults ]

    # now we dump the results/list to a json-file:
    testResultsFile = "testResults_" + outputBaseName + ".json"
    testResultsFile = os.path.join(dirToPutOutputFile, testResultsFile)
    write_json(testResultsFile, allall_results)


def analyzeTestResults_ofSelectedSuite(testResultsJsonFile:str, 
                                       condition:str, # pre or post
                                       suiteName:str, 
                                       suiteSelectionFunction):

    """
    Given a json-file containing tests-results as produce by the function exportLLMPTestResults(),
    this will calculate the verdict per-candidate (e.g. whether the candidate is accepted or rejected),
    judged by a selected test-suite. The test-suite is a subset of all the test-cases that are available
    per task/problem, as listed in the input test-results-json file. Which test-cases are included
    is decided by the given suiteSelectionFunction.

    So, per task/problem T, a test-suite S is selected (with the aforementioned selectionFunction),
    then we decide for each candidate for T we use S to decide a verdict: whether the candidate is 
    accepted or rejected. We also calculate for each T statistics like acceptance rate.

    The for thw whole set of tasks, we also produce statistics like average acceptance rate.

    The method returns a tuple (S,TS,V) where S contains some summary statistics for the whole
    set of tasks, TS is a set of per-task-statistics, and V is the whole set of the raw verdicts
    per candidate.
    """
    with open(testResultsJsonFile, "r") as ftrs:
        allTestResults = json.load(ftrs)

    # drop tasks with empty results e.g. if we ask for pre-cond results,
    # but the task has no pre-cond
    allTestResults = [ taskResults for taskResults in allTestResults 
                                   if taskResults[f"{condition}_condition"] != None ]
  
    numberOfTasks = len(allTestResults)

    if numberOfTasks == 0 : return None

    perTask_summaries = []
    all_verdicts = []
    for T in allTestResults:
        tId = T ["task_id"]
        taskTestResults = T[f"{condition}_condition"]
        if taskTestResults == None : continue

        # taskTestResults contains the test-results of one or more candidate pre/post-conditions
        # as in [ test-results-candidate1, test-results-candidate2, ... ]

        T_verdicts = []
        # iterating over the test-results of each candidate, and calculate for each candidate
        # the verdict e.g. if the candidate-postcond is accepted by the selected test-suite
        for candidateTestResults in taskTestResults:
            # first get the suite over which we will decide a verdict:
            selectedSuite = suiteSelectionFunction(candidateTestResults)
            V = {
                "verdict" : compare_results([ r["expected"] for r in selectedSuite], [ r["result"] for r in selectedSuite]),
                "#tests"  : len(selectedSuite),
                "#passed" : len([ 1 for r in selectedSuite if r["result"] == r["expected"] ])
            }
            # get the verdict, and add it to the list of all verdicts:
            T_verdicts.append(V)

        # collect the raw verdicts:
        all_verdicts.append({
            "task_id" : tId,
            "testsuite-name" : suiteName,
            "verdicts" : T_verdicts,
        })

        # calculate the summaries of this task:
        numOfAccepted = len([ 1 for v in T_verdicts if v["verdict"] == "accepted" ])
        numOfWeaklyAccepted = len([ 1 for v in T_verdicts if v["verdict"] in ["accepted", "too_strong", "too_weak" ]])
        averageTCsPassRate = statistics.mean([ 0 if v["#tests"]==0 else v["#passed"]/v["#tests"] for v in T_verdicts ])
        numberOfCandidates = len(taskTestResults)
        #numberOfTests = T_verdicts[0]["#tests"]
        numberOfTests = statistics.mean([ v["#tests"] for v in T_verdicts ]) 
        Z = {
            "task_id" : tId,
            "testsuite-name" : suiteName,
            "numOfAccepted" : numOfAccepted,
            "numOfWeaklyAccepted" : numOfWeaklyAccepted,
            "accepted@1" : numOfAccepted/numberOfCandidates,
            "weaklyaccepted@1" : numOfWeaklyAccepted/numberOfCandidates,
            "acceptedAtLeastOne" : numOfAccepted>0,
            "weaklyacceptedAtLeastOne" : numOfWeaklyAccepted>0,
            "averageTCsPassRate" : averageTCsPassRate,
            "#tests" : numberOfTests
        }
        # collect the summaries:
        perTask_summaries.append(Z)

    # return a summary over the whole test-results, and the set of
    # verdicts:
    return (
        # top-level summary:
        {
        "cond-type"       : f"{condition}_condition",
        "testsuite-name"  : suiteName,
        "#tasks"          : numberOfTasks,
        "avrg_accepted@1"       : statistics.mean([T["accepted@1"] for T in perTask_summaries]),
        "avrg_weaklyaccepted@1" : statistics.mean([T["weaklyaccepted@1"] for T in perTask_summaries]),
        "acceptedAtLeastOne_percentage" : statistics.mean([1 if T["acceptedAtLeastOne"]==True else 0 for T in perTask_summaries ]),
        "weaklyacceptedAtLeastOne_percentage" : statistics.mean([1 if T["weaklyacceptedAtLeastOne"]==True else 0 for T in perTask_summaries ]),
        "averageTCsPassRate" : statistics.mean([T["averageTCsPassRate"] for T in perTask_summaries]),
        "tot #tests" : sum([T["#tests"] for T in perTask_summaries])
        }
        # per-task-summaries:
        , perTask_summaries
        # the underlying verdicts:
        , all_verdicts
    )

def analyzeTestResults(testResultsJsonFile:str, dirToPutOutputFiles:str):
    """
    Given a json-file containing tests-results as produce by the function exportLLMPTestResults(),
    this will calculate verdicts per candidate and produce per-task statistics and
    statistics for whole set of tasks.

    Various analysis results are saved to files. Additionally, top-level statistics are 
    returned.
    """

    # we choose several test suites here:
    fsuite_HuP   = lambda S : [ t for t in S if t["suite"] == "human-positive"]
    fsuite_HuN   = lambda S : [ t for t in S if t["suite"] == "human-negative"]
    fsuite_HuPN  = lambda S : fsuite_HuP(S) + fsuite_HuN(S)
    fsuite_HuV   = lambda S : [ t for t in S if t["suite"] == "human-validation"]
    fsuite_HuAll = lambda S : fsuite_HuPN(S) + fsuite_HuV(S)
    fsuite_PyP   = lambda S : [ t for t in S if t["suite"] == "pynguin_positive"]
    fsuite_PyN   = lambda S : [ t for t in S if t["suite"] == "pynguin_negative"]
    fsuite_PyAll = lambda S : fsuite_PyP(S) + fsuite_PyN(S)
    fsuite_HuPyP = lambda S : fsuite_HuP(S) + fsuite_PyP(S)
    fsuite_HuPyPNPN = lambda S : fsuite_HuPN(S) + fsuite_PyP(S) + fsuite_PyN(S)
    fsuite_All      = lambda S : fsuite_HuAll(S) + fsuite_PyAll(S)
    
    results_preconds = [
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "pre", "human-positive", fsuite_HuP),
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "pre", "human-all", fsuite_HuAll),
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "pre", "all", fsuite_All)
    ]

    results_postconds = [
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "post", "human-positive", fsuite_HuP),
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "post", "human-set1", fsuite_HuPN),
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "post", "human-all", fsuite_HuAll),
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "post", "positive", fsuite_HuPyP),
        analyzeTestResults_ofSelectedSuite(testResultsJsonFile, "post", "all", fsuite_All)
    ]

    def topLevelSummries(data): 
        return [ r[0] for r in data if r != None]
    def perTaskSummaries(data):
        return [ { "testsuite-name" : r[0]["testsuite-name"],
                   "results" : r[1] } 
                   for r in data if r != None]
    def rawVerdicts(data):
        return [ { "testsuite-name" : r[0]["testsuite-name"],
                   "verdicts" : r[2] } 
                   for r in data if r != None]
    
    # we now save the analysis into files
    testResultsJsonFile_BaseName = os.path.basename(testResultsJsonFile)
    testResultsJsonFile_BaseName = os.path.splitext(testResultsJsonFile_BaseName)[0]
    # drop the "testResults_" prefix
    outputfileBaseName = testResultsJsonFile_BaseName[ len("testResults_") : ]

    file = os.path.join(dirToPutOutputFiles, "preCondAnalysisSummary_" + outputfileBaseName + ".json")
    write_json(file, topLevelSummries(results_preconds))
    file = os.path.join(dirToPutOutputFiles, "preCondAnalysisPerTaskSummaries_" + outputfileBaseName + ".json")
    write_json(file, perTaskSummaries(results_preconds))
    file = os.path.join(dirToPutOutputFiles, "preCondAnalysisRawVerdicts_" + outputfileBaseName + ".json")
    write_json(file, rawVerdicts(results_preconds))

    file = os.path.join(dirToPutOutputFiles, "postCondAnalysisSummary_" + outputfileBaseName + ".json")
    write_json(file, topLevelSummries(results_postconds))
    file = os.path.join(dirToPutOutputFiles, "postCondAnalysisPerTaskSummaries_" + outputfileBaseName + ".json")
    write_json(file, perTaskSummaries(results_postconds))
    file = os.path.join(dirToPutOutputFiles, "postCondAnalysisRawVerdicts_" + outputfileBaseName + ".json")
    write_json(file, rawVerdicts(results_postconds))
    
    #print (f"{topLevelSummries(results_postconds)}")
    
    return (outputfileBaseName, topLevelSummries(results_preconds), topLevelSummries(results_postconds))

       
def executeSolutionPrePostCond(datasetFile:str, Tid:str, condTy:str, tc:list):
    """
    Give a testcase to be run by the solution pre/post-condition of a given problem 
    (specified by the problem-id Tid). 
    """
    dataset = read_problems(datasetFile)
    r = executeSolutionPrePostCondWorker(dataset,Tid,condTy,tc)
    return r

def executeSolutionPrePostCondWorker(dataset:Dict, Tid:str, condTy:str, tc:list):
    """
    The worker-function of executeSolutionPrePostCond. You can pass the json to this worker-function,
    so if you call it multiple times you don't have to keep reading the json from its file.
    """
    T = dataset[Tid]
    fx = f"{condTy}_condition_solution"
    if not (fx in T) or T[fx] == None or T[fx] == "" : return None
    funcDef = T[fx]
    funcName = f"check_{condTy}_solution_{Tid}"  
    try :
        exec(funcDef,globals())
    except:
        print(f">>> Fail to load the definition of the solution of {condTy}-cond of {Tid}")
        return None
    # both work:
    #eval(f"{funcName}(*{tc})")
    r = eval(f"{funcName}(*tc)")
    return r
    

def executeLLMProposal(datasetFile:str, outputjsonFile:str, Tid:str, condTy:str, proposalIndex:int, tc:list):
    """
    Give a test-case tc to the LLM proposal for pre/post-cond of task Tid.

    LLM proposals are read from a json-output file specified by outputjson. You also need to give
    the dataset-file.

    condTy specifies whether it is a pre- or post-condition proposal that you want to execute.
    proposalIndex specifies the proposal-index of the proposal you want to execute.

    That proposal will be grabbed from the json-file, then loaded into memory, and then the testcase tc
    is given to it to be evaluated. This results in either true or false. Or None, if something went
    wrong.

    The tc is a list of values. If the proposal is a post-condition, the first element of tc should
    represent the return value of the program that is being specified by the post-cond.
    """
    dataset = read_problems(datasetFile)
    with open(outputjsonFile, "r") as fp:
        outputjson = json.load(fp)
    r = executeLLMProposalWorker(dataset,outputjson,Tid,condTy,proposalIndex,tc)
    return r

def executeLLMProposalWorker(dataset:Dict, outputjson:Dict, Tid:str, condTy:str, proposalIndex:int, tc:list):
    """
    This is the worker-function of executeLLMProposal. You can pass the jsons to this worker-function,
    so if you call it multiple times you don't have to keep reading them from their files.
    """
    T = dataset[Tid]
    fx = f"{condTy}_condition_incomplete"
    if not (fx in T) or T[fx] == None or T[fx] == "" : return None
    header0 = T[fx]
    params = header0[header0.find("("):]
    funcName = f"check_{condTy}_{Tid}_{proposalIndex}"  
    funcHeader = "def " + funcName + params

    for R in outputjson:
        if R["task_id"] == Tid:
            completions = R[condTy + "_condition_completions"]
            body = completions[proposalIndex]
            if body == None or body == "" : return None
            funcDummyDef = funcHeader + "\n   raise(\"dummy function invoked!\")"
            funcDef      = funcHeader + "\n" + body + "\n"
            if DEBUG: print(funcDef)
            try :
                # do the dummy-def first to make sure that we wipe previous def.
                exec(funcDummyDef,globals())
                exec(funcDef,globals())
            except:
                print(f">>> Fail to load the definition of {proposalIndex}-th proposal of {condTy}-cond of {Tid}")
                return None
            # both work:
            #eval(f"{funcName}(*{tc})")
            r = eval(f"{funcName}(*tc)")
            return r
    return None


def executeExternalSuite(datasetFile:str, outputjsonFile:str, suitename:str, testsuiteJsonFile:str):
    """
    Execute external test-suites and return the resulting test-results on all LLM pre/post candidates
    in the outputjsonFile. 
    
    The suitename specifies how the suites will be named in the resulting list of test-results.
    """
    with open(testsuiteJsonFile, "r") as fp:
        testsuite = json.load(fp)

    def getTestSuite(str):
        if str == []: 
            return []
        return eval(str)

    # we'll just merge the positive and negative tests; we will re-check the polarity later and
    # re-assign the polarity accordingly:
    testsuite_pre  = { task["problemId"] : getTestSuite(task[f"positive_pre_tests"]) + getTestSuite(task[f"negative_pre_tests"])
                       for task in testsuite}
    testsuite_post = { task["problemId"] : getTestSuite(task[f"positive_post_tests"]) + getTestSuite(task[f"negative_post_tests"])
                       for task in testsuite}
    print(f"** #problems for precond with some tests: {len([1 for s in testsuite_pre.values() if s != []])}")
    for Tid in testsuite_pre:
        P = testsuite_pre[Tid]
        print(f"  {Tid} #precond tests: {len(P)}")
    print(f"** #problems for postcond with some tests: {len([1 for s in testsuite_post.values() if s != []])}")
    for Tid in testsuite_post:
        P = testsuite_post[Tid]
        print(f"  {Tid} #postcond tests: {len(P)}")
        
    S1 = executeExternalSuiteWorker(datasetFile,outputjsonFile,"pre",suitename,testsuite_pre)
    S2 = executeExternalSuiteWorker(datasetFile,outputjsonFile,"post",suitename,testsuite_post)
    return (S1,S2)

    

def executeExternalSuiteWorker(datasetFile:str, outputjsonFile:str, 
                               condTy:str, # pre or post
                               suitename:str, testsuite:Dict):
    """
    Worker of executeExternalSuite. The external test suites to execute are given as a dictionary.
    """
    dataset = read_problems(datasetFile)
    with open(outputjsonFile, "r") as fp:
        outputjson = json.load(fp)
    outputjsonDict = { task["task_id"] : task for task in outputjson }
    all_test_results = {}
    for Tid in dataset:
        llm_proposals = outputjsonDict[Tid][f"{condTy}_condition_completions"]
        if llm_proposals == None:
            continue
        T_suite = testsuite[Tid]
        if len(T_suite) == 0:
            continue

        solution_test_results = []
        for tc in T_suite:
            # run the tc on the solution pre/post-cond:
            # hmm... should add timeout here?
            result1 = executeSolutionPrePostCondWorker(dataset,Tid,condTy,tc)
            solution_test_results.append(result1)
        
        llm_test_results = []
        for k in range(0,len(llm_proposals)):
            proposal_k_results = []
            for (tc, expected) in zip(T_suite, solution_test_results) :
                try:
                    print(f">>> about to execute {k}-th proposal of {condTy}-cond of {Tid}")
                    # r = executeLLMProposalWorker(dataset,outputjson,Tid,condTy,k,tc)
                    # run it with timeout:
                    r = func_timeout(myconfig.RUN_SINGLE_TESTCASE_TIMEOUT, 
                                     executeLLMProposalWorker, 
                                     args=[dataset,outputjson,Tid,condTy,k,tc])
                    print(">>> exec-done")
                    if (r==None) or (type(r) != bool) : 
                        r = "not a bool"
                except FunctionTimedOut:
                    if DEBUG: print(f">>> {k}-th proposal of {condTy}-cond of {Tid} timed-out on input {tc}")  
                    r = "timeout"
                except:
                    if DEBUG: print(f">>> {k}-th proposal of {condTy}-cond of {Tid} crashed on input {tc}")  
                    r = "failed" 
                tag = "positive" if expected == True else "negative"
                proposal_k_results.append({
                    "suite" : f"{suitename}_{tag}",
                    "test"  : f"{tc}",
                    "result" : r,
                    "expected" : expected
                })
            llm_test_results.append(proposal_k_results)
        all_test_results[Tid] = llm_test_results
    return all_test_results

def extendTestResultsWithExternalSuite(datasetFile:str, 
                                       outputjsonFile:str, 
                                       baseTestResultsJsonFile:str,
                                       suitename:str, 
                                       testsuiteJsonFile:str,
                                       dirToPutOutputFile:str):
    
    """
    Extend existing test-results with additional tests.
    """
    with open(baseTestResultsJsonFile, "r") as ftr:
        baseTestResults = json.load(ftr)
        baseTestResultsDict = { T["task_id"] : T  for T in baseTestResults }

    def extendWith(newtests, condTy):
        for Tid in newtests:
            baseTest = baseTestResultsDict[Tid]
            if newtests[Tid] == []: continue
            if baseTest[f"{condTy}_condition"] == None:
               baseTest[f"{condTy}_condition"] = newtests[Tid]
            else:        
               baseTest[f"{condTy}_condition"] =  [ S1 + S2 for (S1,S2) in zip(baseTest[f"{condTy}_condition"],newtests[Tid]) ]

    (precond_tests, postcond_tests) = executeExternalSuite(datasetFile,outputjsonFile,suitename,testsuiteJsonFile)
    extendWith(precond_tests, "pre")
    extendWith(postcond_tests, "post")

    extendedTestResults = baseTestResults
    # save the extended test-suites
    testResultsJsonFile_BaseName = os.path.basename(baseTestResultsJsonFile)
    file = os.path.join(dirToPutOutputFile, "extended" + testResultsJsonFile_BaseName)
    write_json(file, extendedTestResults)
    return extendedTestResults

# example use:
if __name__ == '__main__':
   ROOT = os.path.dirname(os.path.abspath(__file__))
   dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "HEx-compact.json")
   outputjson = os.path.join(ROOT, "results", "bla_all_usePrgDesc_04_02_2025_17_16_45.json")
   outputjson2 = os.path.join(ROOT, "results", "claude-3_all_usePrgDesc_27_02_2025_17_51_06.json")
   outputjson3 = os.path.join(ROOT, "results", "gpt-4o_all_usePrgDesc_03_02_2025_22_18_27.json")
   testreultsjson = os.path.join(ROOT, "results", "testResults_claude-3_all_usePrgDesc_27_02_2025_17_51_06.json")
   odir = os.path.join(ROOT, "results")

   #exportOutLLMProposals(dataset,outputjson,odir)

   #r = executeSolutionPrePostCond(dataset,"HE1","post",[["()","()"],"()()"])
   #print(r)
   r = executeSolutionPrePostCond(dataset,"HE0","post",[False, [3550], 3550])
   print(r)

   #r = executeLLMProposal(dataset,outputjson,"HE1","post",0,[["()","()"],"()()"])
   #print(r)
   r = executeLLMProposal(dataset,outputjson3,"HE0","post",0,[False, [3550], 3550])
   print(r)
   r = executeLLMProposal(dataset,outputjson3,"HE0","post",0,[False, [False, True, False, False], True])
   print(r)

   #r = executeExternalSuite(dataset,outputjson2,"pynguin",os.path.join(ROOT, "results", "coba-postmortem","pynguin_hex_generatedTests.json"))
   #r0 = r[1]["HE101"]
   #print(f">>> {r0}")

   #r = extendTestResultsWithExternalSuite(dataset,
   #                                       outputjson2,
   #                                       testreultsjson,
   #                                       "pynguin",
   #                                       os.path.join(ROOT, "results", "coba-postmortem","pynguin_hex_generatedTests.json"),
   #                                       os.path.join(ROOT, "results"))
   #
   #r0 ={ T["task_id"] : T for T in r }["HE101"]
   #print(f">>> {r0}")

   #exportLLMPTestResults(dataset,outputjson,odir)
   #analyzeTestResults(testreultsjson,odir)
