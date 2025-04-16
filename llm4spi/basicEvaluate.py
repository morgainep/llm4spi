#
# Contain functions for performing the LLM basic evaluation towards the pre-/post-conditions
# tasks. In this evaluation we run the provided test cases and collect the results. 
# Per task/problem, the LLM would provide one or more candidates for the pre- and
# post-condition of the task (depending on the task, it may not have a pre-cond, but will
# always have a post-cond).
# 
# For each task T, and for each candidate C, we will collect the result of running T's test
# suites on C. Each task has two or more test suites. And each test suite consists of 
# several test-case.
# Running a test-case on e.g. a candidate post-cond gives three possible outcomes: 
#    (1) a value True is returned
#    (2) a False is returned
#    (3) failed, e.g. because the execution returned a non-boolean value, or it crashed.
#
# In addition to collecting the full test-results, some basic statistics will also be
# calculated and provided.  
#
from typing import Dict
import textwrap
import data
from collections import Counter
import time
from func_timeout import func_timeout, FunctionTimedOut
import myconfig
import similarity
import statistics

DEBUG = True

def compare_results(expected: list, predicted: list) -> str:
    """
    Returns a judgement after comparing the predicted results (results from running the function produced
    by AI) with of the expected results.

    Note: (**) the comparison can be configured (see myconfig.py) such that None as a prediction 
          will be interpreted as 'making no prediction', and will be excluded from judgement.
          However, if all predications are None, a 'failed' judgement is returned.

    Judgement:
    (1) 'accepted' if all predictions (excluding None-values) match the expected values.
    (2) 'failed' if AI solution crashed, or it produces a value that is not even a boolean,
        or if all predications are None.
    (3) 'too_weak' if for every not-None prediction p and the corresponding expected value e
                   we have e ==> p
    (4) 'too_strong' if for every not-None prediction p and the corresponding expected value e
                   we have p ==> e
    (5) 'rejected' if none of the above is the case. 

    """

    if myconfig.IGNORE_NONE_PREDICTION: 
        # special case (**) above
        # filter first the None-predictions
        zz = [ (e,p) for (e,p) in zip(expected,predicted) if p != None ]
        if len(zz) == 0:
            # if all predictions are None, we declare "fail":
            return "failed"
        # only inspect the expecteds and predictions for which the predictions are not None:
        expected   = [ e for (e,p) in zz ]
        predicted = [ p for (e,p) in zz ]

    #print(f">>> evaluated expecteds: {expected}")
    #print(f">>> evaluated predictions: {predicted}")

    if any((prediction == "failed") |  (type(prediction) != bool) for prediction in predicted):
        return "failed"
    
    if expected == predicted:
        return "accepted"
    
    any_false_negative = False
    any_false_positive = False

    for (expectation,prediction) in zip(expected,predicted):
        any_false_negative = any_false_negative or (expectation and (not prediction))
        any_false_positive = any_false_positive or ((not expectation) and prediction)
    
    if any_false_negative & any_false_positive:
        return "rejected"
    if any_false_negative:
        return "too_strong"
    if any_false_positive:
        return "too_weak"
    
    return "failed"
    

def try_check_condition(test_case, task_id, condType): # pre or post
    """
    Run a single test-case on an AI-proposed solution. The solution is 
    assumed to have been loaded into the memory, and is named
    e.g. check_post_taskid, for post-condition.
    """
    def runit(tc):
        # the 'tc' below should be {tc}, but it works too as below, accidentally, in this case,
        # the way eval works...
        result = eval(f"check_{condType}_{task_id}(*tc)")
        return result
    
    try:
        #result = eval(f"check_post_{task_id}(*test_case)")
        # run the pre/post-cond in the testcase; impose time out too:
        result = func_timeout(myconfig.RUN_SINGLE_TESTCASE_TIMEOUT, runit, args=[test_case])
        if result != None and type(result) != bool:
            # some proposal returns a lambda-function!! which later gives a problem at the json serialization
            # we'll override it here:
            result = "not a boolean value"

    except FunctionTimedOut:
        print(">>> An AI solution execution on a test-case is killed due to timed out.")
        return "failed"
    except Exception as e:
        #print(f">>> CRASH {e}")
        return "failed"
    return result


def listSplit(s:list, sep): 
    """
    split the list s into segments which are separated by sep
    """
    segments = []
    z = []
    for x in s:
        if x==sep:
            segments.append(z)
            z = []
        else:
            z.append(x)
    segments.append(z)
    return segments

def extractTests(condition:str, task:Dict):
    """
    Each task comes with test cases, which may be grouped into test suites.
    If so, the suites are separeted by a '===' token. In the current format,
    there will be at most three suites.
    This function will extract the test suites available in a task. 
    """
    # if the test-cases are marked with a split token, this indicates that
    # they consists of two groups: base-group and validation-group.
    # We separate them:
    splitToken = '==='
    test_cases0 = eval(task[f"{condition}_condition_tests"])
    test_suites = listSplit(test_cases0,splitToken)
    suite_Base0 = test_suites[0]
    suite_Base1 = []
    suite_Validation = []
    if len(test_suites) == 2:
       suite_Validation = test_suites[1]
    elif len(test_suites) > 2: 
        suite_Base1 = test_suites[1]
        for suite in test_suites[2:] : suite_Validation.extend(suite)
    else:
        # should not happen... but if this does happen,
        # then we simply have no validation suite
        suite_Validation = []
    return {
        "suite_Base0" : suite_Base0,
        "suite_Base1" : suite_Base1,
        "suite_Validation" : suite_Validation
    }

def evaluate_task_result(task: Dict, condition: str):
    """
    Given a single task T, described as a dictionary. This dictionary
    is expected to already contain the set of candidates produced by the AI 
    for either the pre- or post-conditon of the task T. 

    This function iterates over those candidates to run a basic evaluation. 
    This means that for  every candidate C, we will run the test suites in 
    T on this candidate and collect the results of every test-case in the suites.
    In addition to collecting raw test results, some basic analyses will also
    be done and included. More elaborate analyses can be done later as post-processing
    on the collected data.

    The condition argument is a selector. It is either 'pre' or 'post'. E.g. use
    'pre' to run this raw-evaluation on candidates pre-cond of P, and use 'post'
    to run the raw-evaluation on the candidates post-cond.

    The collected results are added/updated as entries into the dictionary that
    represents the task (by side effect on the dictionary).
    """
    Tid = task["task_id"]
    print(f"** Start collecting raw results for Task {Tid}, {condition}-condition")

    task[f"{condition}_condition_reference_TestResults"]  = None
    task[f"{condition}_condition_candidates_TestResults"] = None
    task[f"{condition}_condition_ResultsSummary"] = None

    # we first handle the case when the task pre- or post-condition
    # does not exists:
    if not (f"{condition}_condition_solution" in task) : 
        return
    solution_function = task[f"{condition}_condition_solution"]
    if solution_function==None or solution_function=="":
        return
    
    # The task pre-/post- exists, we proceed. First we will execute the test suites on
    # the solution pre/post-cond

    # executing the solution-function def; not expecting it to fail
    #complete_solution_function = task[f"{condition}_condition_incomplete"] + "\n" + indented_solution_function_body
    try:
        exec(solution_function,globals())
    except:
        print(">>>>>> Ouch. The def of the solution function CRASHED!")
        print(solution_function)
        return

    # if the test-cases are marked with a split token, this indicates that
    # they consists of two groups: base-group and validation-group.
    # We separate them:
    testSuites = extractTests(condition,task)
    suite_Base0 = testSuites["suite_Base0"]
    suite_Base1 = testSuites["suite_Base1"]
    suite_Validation = testSuites["suite_Validation"]

    # executing the test-cases on the solution-function, also not expecting these
    # to fail:
    print(f"  Running test suites on the reference solution. #Base0={len(suite_Base0)}, #Base1={len(suite_Base1)}, #Validation={len(suite_Validation)}")
    reference_results_Base0 = [eval(f"check_{condition}_solution_{Tid}(*test_case)") for test_case in suite_Base0]
    reference_results_Base1 = [eval(f"check_{condition}_solution_{Tid}(*test_case)") for test_case in suite_Base1]
    reference_results_Validation = [eval(f"check_{condition}_solution_{Tid}(*test_case)") for test_case in suite_Validation]

    R = {
        "base0" : reference_results_Base0,
        "base1" : reference_results_Base1,
        "validationSuite" : reference_results_Validation
    }
    task[f"{condition}_condition_reference_TestResults"]  = R
    if DEBUG:
        print(solution_function)
        print("   Reference tests results:")
        print(f"  {R}")

    #
    # Now we run the tests on each of the candidates from the AI:
    #

    # get all the AI-completions, indent each one of them as well:
    AI_completions = [ textwrap.indent(body,'    ') if body != None else '' for body in task[f"{condition}_condition_completions"] ]
    # now, evaliate each candidate-completion:
    tasks_results = [] 

    for k in range(len(AI_completions)):
        indented_function_body = AI_completions[k]
        complete_function = task[f"{condition}_condition_incomplete"] + "\n" + indented_function_body
        dummy_function = task[f"{condition}_condition_incomplete"] + "\n   raise(\"dummy function invoked!\")"

        U = { "nr" : k }
        tasks_results.append(U)
    
        # executing the def. of the AI's function; it may fail (e.g. if AI's code is not even syntax correct)
        try:
            exec(dummy_function,globals())
            exec(complete_function,globals())
            U["def-loaded"] = "success"
        except:
            print(f">>>>>> The def of completion-proposal {k} crashed!")
            print(f">>>>>> src:\n {complete_function}")
            U["def-loaded"] = "failed"
            continue
    
        print(f"      Running tests on candidate {k}")

        # running the test-cases on the AI's function; this may fail too:
        results_Base0 = [try_check_condition(test_case, task["task_id"],condition) for test_case in suite_Base0]
        results_Base1 = [try_check_condition(test_case, task["task_id"],condition) for test_case in suite_Base1]
        results_Validation = [try_check_condition(test_case, task["task_id"],condition) for test_case in suite_Validation]

        U["base0"] =  results_Base0
        U["base1"] =  results_Base1
        U["validationSuite"] =  results_Validation
        U["base0-verdict"] = compare_results(reference_results_Base0, results_Base0)
        U["allBases-verdict"] = compare_results(
                                        reference_results_Base0 + reference_results_Base1, 
                                        results_Base0 + results_Base1)
        U["validation-verdict"] = compare_results(reference_results_Validation, results_Validation)
        U["allsuites-verdict"] = compare_results(
                                        reference_results_Base0 + reference_results_Base1 + reference_results_Validation, 
                                        results_Base0 + results_Base1 + results_Validation)
        U["editDistance"] = similarity.levenshteinDistance(solution_function,complete_function)["relativeDistance"]

        if DEBUG:
            print(f"   Candidate {k}:")
            print(complete_function)
            print(f"   Candidate {k} tests results:")
            print(f"  {R}")
    
    task[f"{condition}_condition_candidates_TestResults"] = tasks_results
    nonCrashes = [ V for V in tasks_results if V["def-loaded"] == "success" ]
    defCrashes = len(tasks_results) - len(nonCrashes)
    base0_accept       = len([ 1 for V in nonCrashes if V["base0-verdict"]=="accepted"])
    base0_tooWeak      = len([ 1 for V in nonCrashes if V["base0-verdict"]=="too_weak"])
    base0_tooStrong    = len([ 1 for V in nonCrashes if V["base0-verdict"]=="too_strong"])
    allBases_accept    = len([ 1 for V in nonCrashes if V["allBases-verdict"]=="accepted"])
    allBases_tooWeak   = len([ 1 for V in nonCrashes if V["allBases-verdict"]=="too_weak"])
    allBases_tooStrong = len([ 1 for V in nonCrashes if V["allBases-verdict"]=="too_strong"])
    allTests_accept    = len([ 1 for V in nonCrashes if V["allsuites-verdict"]=="accepted"])

    summary = {
        "defCrashes"         : defCrashes,
        "base0_accept"       : base0_accept,
        "base0_tooWeak"      : base0_tooWeak,
        "base0_tooStrong"    : base0_tooStrong,
        "allBases_accept"    : allBases_accept,
        "allBases_tooWeak"   : allBases_tooWeak,
        "allBases_tooStrong" : allBases_tooStrong,
        "allTests_accept"    : allTests_accept,
        "allBasesAccept_avrg_editDist" : None,
        "allBases_tooWeakOrStrong_avrg_editDist" : None
    }

    task[f"{condition}_condition_ResultsSummary"] = summary

    print(f"   #chrashes = {defCrashes}")
    print(f"   #base0-accept        = {base0_accept}")   
    print(f"   #base0-too-weak      = {base0_tooWeak}")   
    print(f"   #base0-too-strong    = {base0_tooStrong}")   
    print(f"   #allBases-accept     = {allBases_accept}")   
    print(f"   #allBases-too-weak   = {allBases_tooWeak}")   
    print(f"   #allBases-too-strong = {allBases_tooStrong}")   
    print(f"   #ALLTESTS=ACCEPT     = {allTests_accept}")   

    if allBases_accept > 0 :
        allBasesAccept_avrg_editDist = statistics.mean([ V["editDistance"] for V in nonCrashes if V["allBases-verdict"]=="accepted"])
        summary["allBasesAccept_avrg_editDist"] = allBasesAccept_avrg_editDist
        print(f"   allBases-accept avrg-dist = {allBasesAccept_avrg_editDist}")  
    if allBases_tooWeak + allBases_tooStrong > 0 :
        allBases_tooWeakOrStrong_avrg_editDits = statistics.mean([ V["editDistance"] for V in nonCrashes if V["allBases-verdict"] in {"too_weak", "too_strong"}])
        summary["allBases_tooWeakOrStrong_avrg_editDist"] = allBases_tooWeakOrStrong_avrg_editDits
        print(f"   allBases-too-weak-or-strong avrg-dist = {allBases_tooWeakOrStrong_avrg_editDits}")  
    
 

def mk_results_summary(tasks: Dict[str,Dict]) -> tuple :
    """
    Construct summaries for the results of the whole dataset.
    """
    def worker(summary,condType): # pre or post

        hasResults = [ T[f"{condType}_condition_ResultsSummary"] for T in tasks.values() if T[f"{condType}_condition_ResultsSummary"] != None ]
        
        numOf_base0_accept       = len([ 1 for S in hasResults if S["base0_accept"] > 0])
        numOf_base0_tooWeak      = len([ 1 for S in hasResults if S["base0_tooWeak"] > 0])
        numOf_base0_tooStrong    = len([ 1 for S in hasResults if S["base0_tooStrong"] > 0])
        numOf_base0_weakAccept   = len([ 1 for S in hasResults if S["base0_accept"] > 0 or S["base0_tooWeak"] > 0 or S["base0_tooStrong"] > 0])
        numOf_allBases_accept    = len([ 1 for S in hasResults if S["allBases_accept"] > 0])
        numOf_allBases_tooWeak   = len([ 1 for S in hasResults if S["allBases_tooWeak"] > 0])
        numOf_allBases_tooStrong = len([ 1 for S in hasResults if S["allBases_tooStrong"] > 0])
        numOf_allBases_weakAccept = len([ 1 for S in hasResults if S["allBases_accept"] > 0 or S["allBases_tooWeak"] > 0 or S["allBases_tooStrong"] > 0])
        numOf_allTests_accept    = len([ 1 for S in hasResults if S["allTests_accept"] > 0])

        summary["#tasks"] = len(hasResults)
        summary["accepted by base0-tests"] = numOf_base0_accept
        summary["weakly accepted by base0-tests"] = numOf_base0_weakAccept
        summary["accepted by all-base-tests"] = numOf_allBases_accept
        summary["weakly accepted by all-base-tests"] = numOf_allBases_weakAccept
        summary["accepted by all-tests"] = numOf_allTests_accept

        editDistances1 = [ S["allBasesAccept_avrg_editDist"] 
                                for S in hasResults 
                                if S["allBasesAccept_avrg_editDist"] != None ]
        if len(editDistances1) > 0 :
            summary["allBasesAccept_avrg_editDist"] = statistics.mean(editDistances1)
        else: 
            summary["allBasesAccept_avrg_editDist"] = None

        editDistances2 = [ S["allBases_tooWeakOrStrong_avrg_editDist"] 
                                for S in hasResults 
                                if S["allBases_tooWeakOrStrong_avrg_editDist"] != None
                                ]
        if len(editDistances2) > 0 :
            summary["allBases_tooWeakOrStrong_avrg_editDist"] = statistics.mean(editDistances2)
        else :
            summary["allBases_tooWeakOrStrong_avrg_editDist"] = None
        
        return summary
    

    return (worker({},"pre"), worker({},"post"))

def write_wholeSet_summary(precond_evaluation_summary, 
                               postcond_evaluation_summary,
                               reportfile_basename):
    """
    Printing a summary of the whole evaluation (over all tasks),
    and also save this summary in a file.
    """

    def worker(summary,condType): # pre or post

        tot = summary["#tasks"]
        N0  = summary["accepted by base0-tests"]
        N0b = summary["weakly accepted by base0-tests"]
        N1  = summary["accepted by all-base-tests"]
        N1b = summary["weakly accepted by all-base-tests"] 
        N2  = summary["accepted by all-tests"] 
        
        lev1 = summary["allBasesAccept_avrg_editDist"]
        lev2 = summary["allBases_tooWeakOrStrong_avrg_editDist"]

        percent0  = 0 if tot==0 else 100*N0/tot
        percent0b = 0 if tot==0 else 100*N0b/tot
        percent1  = 0 if tot==0 else 100*N1/tot
        percent1b = 0 if tot==0 else 100*N1b/tot
        percent2  = 0 if tot==0 else 100*N2/tot

        str = ""
        str += f"##{condType}-cond : {tot}"
        str += f"\n   accepted by base0-tests        : {N0} ({percent0}%)"
        str += f"\n   weakly accepted by base0-tests : {N0b} ({percent0b}%)"
        str += f"\n   accepted by all-base-tests     : {N1} ({percent1}%)"
        str += f"\n   weakly accepted by all-base-tests  : {N1b} ({percent1b}%)"
        str += f"\n   accepted by ALL-tests (validation) : {N2} ({percent2}%)"
        str += f"\n   avrg-edit-dist of accepted by all-base-tests               : {lev1}"
        str += f"\n   avrg-edit-dist of too-weak or too-strong on all-base-tests : {lev2}"
        str += "\n"

        print(str)

        if reportfile_basename == None: return
        summaryfile = reportfile_basename.replace("evaluation","summary") + ".txt"
        with open(summaryfile,'a') as F: F.write(str)

    worker(precond_evaluation_summary,"pre")
    worker(postcond_evaluation_summary,"post")


def write_perTask_summaries(tasks: Dict[str,Dict], reportfile_basename:str):
    """
    Write per-task summary to a csv-file.
    """

    numOfColumns = 13

    if reportfile_basename == None: return
    reportfile = reportfile_basename + ".csv"
    with open(reportfile,'w') as f:
        
        def worker(tId,task,condType): # condType is either pre or post

            labelx = f"{condType}_condition_solution"
            if not (labelx in task) or task[labelx] == None or task[labelx] == "" : 
                # the pre/post condition is not present, so no data is collected either:
                return

            str = f"{tId},{tId}-{condType}"

            taskSummary = task[f"{condType}_condition_ResultsSummary"]

            if taskSummary == None:
                str += ",failed"
                N = numOfColumns - 3
                for k in range(N):
                    str += ","

            else :
                str += ",success"
                values = [  taskSummary[f"defCrashes"] ,
                    taskSummary["base0_accept"] ,      
                    taskSummary["base0_tooWeak"] ,  
                    taskSummary["base0_tooStrong"] ,   
                    taskSummary["allBases_accept"] ,  
                    taskSummary["allBases_tooWeak"] ,  
                    taskSummary["allBases_tooStrong"] , 
                    taskSummary["allTests_accept"] ,
                    taskSummary["allBasesAccept_avrg_editDist"] , 
                    taskSummary["allBases_tooWeakOrStrong_avrg_editDist"]
                ]

                for v in values:
                    str += "," if v==None else f",{v}"
            
            str += "\n"
            f.write(str)

        # printing the column-names; there should be 13 of them ...
        f.write("task-id,cond-type")
        f.write(",deploy,crashing-candidates")
        f.write(",base0-accept,base0-tooWeak,base0-tooStrong")
        f.write(",allBases-accept,allBases-tooWeak,allBases-tooStrong,allTests-accept")
        f.write(",allBases-accept-avrg-edit-dist,allBases-tooWeakOrStrong-avrg-edit-dist\n")
        # printing the rows:
        for tId in tasks:
            task = tasks[tId]
            worker(tId,task,"pre")
            worker(tId,task,"post")

def evaluate_tasks_results(tasks: Dict[str,Dict], reportfile_basename:str)  :
    """
    Run the basic evaluation for all the tasks. This iterates over the tasks, and performs
    basic evaluation on each of then.

    The collected data and the evaluation data per task is inserted into each task-dictionary.
    Additionally this function will print and save summaries. One summary for the whole
    dataset will be produced, and a csv-file containing per-task-summaries is also produced.
    """
    for tID in tasks:
        T = tasks[tID]
        evaluate_task_result(T, "pre")
        evaluate_task_result(T, "post")
    summaries = mk_results_summary(tasks)
    write_perTask_summaries(tasks,reportfile_basename)
    write_wholeSet_summary(summaries[0],summaries[1],reportfile_basename)
    

