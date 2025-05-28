#
# Provide a main API for evaluating an LLM on its ability to produce pre-/post-conditions.
# An example is also shown on how to use the API using openAI's GPT as the back-end LLM.
#

from datetime import datetime
from typing import Dict, List
from openai import OpenAI
import os
import time

from data import read_problems, write_json
from prompting import create_prompt
from basicEvaluate import evaluate_tasks_results
from pythonSrcUtils import extractFunctionBody, extractPythonFunctionDef_fromMarkDownQuote, fix_indentation

class PromptResponder:

    def __init__(self) :
        self.DEBUG = False

    """
    A template class that generically represents an LLM/AI that can respond to a prompt 
    to ask its completion.
    """
    def completeIt(self, multipleAnswer:int, prompt:str) -> list[str]:
        """
        Complete the given prompt. Return the answer. As some LLMs can be configured to
        generate multiple answers to the same prompt, the parameter multipleAnswer can be used
        to specify how many asnwers we want from the AI. If its one, the just one answer is 
        expected from the AI. If it is e.g. 3 then three answers are expected. 
        """
        return None

def generate_results(
        AI : PromptResponder, 
        datafile:str,
        specificProblem:str,
        experimentName:str,
        enableEvaluation: bool,
        allowMultipleAnswers: int,
        prompt_type: str        
        )  :
    """
    The general API for evaluating an LLM/AI in its ability to construct pre- and post-conditions
    from their informal descriptions. The AI is generically represented by an PromptResponder-object,
    which has a method takes a prompt-string as input, and returns a new string as the answer 
    to the prompt.
    
    This API takes a dataset as its input, which is a file containing a JSON-list.
    Each item in the list is called a Problem. It represents a program (for now, a Python-function) whose 
    pre- and post-conditions are to be constructed. The program-code and its doc are provided, but the 
    dataset is assumed to already contain separate text-doc for the pre- and post-conditions of the program. 

    If the parameter specificProblem is specified (it is not None), then only the problem with the
    specified id will be evaluated. So, the dataset then is just a singleton-set containing that
    single problem. 
    
    For each Problem in the dataset, the LLM task is to generate a python code that is an executable version 
    of the corresponding pre-/post-condition.
    The dataset is also assumed to contain a reference solution (ground truth) for each pre-/post-condition, 
    along with tests for assessing how good the answer from the AI. 

    For each pre- or post-condition R produced by the AI, the following evaluation result is produced:
       * (1) failed: if R crashes, or if it does not even return a boolean value, or if R
                     returns None on all test-cases.
       * (2) accepted: for every test-input x (provided in the dataset), R(x) = R0(x), where R0 is the provided
                 reference solution. 
                 NOTE: Depending on the configuration in myconfig.py, test inputs for which R(x) gives None 
                 can be interpreted as 'i don't know' and are ignored from the consideration.
                 This also applies for judgement (3) and (4) below.
       * (3) too strong: if R is not accepted, and for every test input x, we have R(x) implies R0(x).
       * (4) too weak:   if R is not accepted, and for every test input x, we have R0(x) implies R(x).
       * (5) rejected: none of the above judgement is the case.

    An evaluation report, along with the produced solutions from the AI are saved in files in /results.
    """
    time0 = time.time()
    tasks = read_problems(datafile)
    timeSpentReadingData = time.time() - time0

    if specificProblem != None:
        tasks = { specificProblem : tasks[specificProblem] }

    time1 = time.time()
    for task in tasks:
        generate_completions(AI, tasks[task], allowMultipleAnswers, prompt_type=prompt_type)
    timeSpentAI = time.time() - time1

    current_date = (datetime.now()).strftime("%d_%m_%Y_%H_%M_%S")

    time2 = time.time()
    reportfile_basename = f"results/{experimentName}_evaluation_{prompt_type}_{current_date}"
    # gathering AI raw-responses and extracted completions:
    results = [{
            "task_id": tasks[Tid]["task_id"],
            "pre_condition_prompt" : tasks[Tid]["pre_condition_prompt"],
            "pre_condition_raw_responses": tasks[Tid]["pre_condition_raw_responses"],
            "pre_condition_completions": tasks[Tid]["pre_condition_completions"],
            "post_condition_prompt" : tasks[Tid]["post_condition_prompt"],
            "post_condition_raw_responses": tasks[Tid]["post_condition_raw_responses"],
            "post_condition_completions": tasks[Tid]["post_condition_completions"]
            } for Tid in tasks]
    
    if enableEvaluation:
        # then do the evaluation
        evaluate_tasks_results(tasks,reportfile_basename)
        # add the eval-summaries and raw-test-results into the results:
        for R in results :
            Tid = R["task_id"]
            task = tasks[Tid]
            condTypes = ["pre","post"]
            for condTy in condTypes:
               R[f"{condTy}_condition_ResultsSummary"] = task[f"{condTy}_condition_ResultsSummary"]
               R[f"{condTy}_condition_reference_TestResults"] = task[f"{condTy}_condition_reference_TestResults"]
               R[f"{condTy}_condition_candidates_TestResults"] = task[f"{condTy}_condition_candidates_TestResults"]
        
    timeSpentAnalysis = time.time() - time2

    # Saving raw responses and evaluation results in a json-file:
    #write_jsonl(f"results/{experimentName}_all_{prompt_type}_{current_date}.jsonl", results)
    write_json(f"results/{experimentName}_all_{prompt_type}_{current_date}.json", results)

    overallTime = time.time() - time0

    runtimeInfo = {
        "time loading data" : timeSpentReadingData,
        "time AI" : timeSpentAI,
        "time analysis" : timeSpentAnalysis,
        "time all" : overallTime
    }

    runtimeInfofile = reportfile_basename.replace("evaluation","runtime") + ".txt"
    with open(runtimeInfofile,'w') as F:
        F.write(f"time loading data:{timeSpentReadingData}\n")
        F.write(f"time AI:{timeSpentAI}\n")
        F.write(f"time analysis:{timeSpentAnalysis}\n")
        F.write(f"time all:{overallTime}")

    print( "** Time:")
    print(f"   time loading data: {timeSpentReadingData}")
    print(f"   time AI: {timeSpentAI}")
    print(f"   time analysis: {timeSpentAnalysis}")
    print(f"   time all: {overallTime}")
    # DONE

def fix_completionString(header:str, completion:str) -> str :
    """
    Try to fix the completion string sent by AI, e.g. by stripping of
    the function header (we will only ask it to return function bodies). 
    """
    if completion==None: return None
    completion = extractPythonFunctionDef_fromMarkDownQuote(completion)
    body1 = extractFunctionBody(completion)
    body2 = fix_indentation(header,body1)
    if body2 != None :
        return body2
    return body1

    
def generate_completions(
        AI: PromptResponder,
        task: Dict,
        allowMultipleAnswers: int,
        prompt_type: str) -> Dict:
    """
    This function takes the desciption of a task/problem, represented as a dictionary.
    It then creates the completion prompt for the pre- and post-condition for the task. 
    The prompt is sent to an AI model and the answers (the completions, one or more)
    are collected. The answers are added into the task-dictionary.

    The AI is generically represented by an object of class PromptResponder, which has
    a method that takes a prompt-string and returns a string (the answer).

    The creation of the prompt is coded in the module Prompting. 
    """
    def worker(condType): # pre or post
        prompt = create_prompt(task, condition_type=condType, prompt_type=prompt_type)
        task[condType + "_condition_prompt"] = prompt
        task[condType + "_condition_raw_responses"] = None
        task[condType + "_condition_completions"]   = None
        if prompt != None:
            # note that this gives one or more answers, in a list:
            completions = AI.completeIt(allowMultipleAnswers,prompt)
            task[condType + "_condition_raw_responses"] = completions
            header = task[condType + "_condition_incomplete"]
            task[condType + "_condition_completions"] = [ fix_completionString(header,rawAnswer) for rawAnswer in completions ]
  
    worker("pre")
    worker("post")
    return task

class MyOpenAIClient(PromptResponder):
    """
    An instance of prompt-responder that uses openAI LLM as the backend model.
    """
    def __init__(self, client: OpenAI, modelId:str):
        PromptResponder.__init__(self)
        self.client = client
        self.model = modelId 
        # Various OpenAI LLMs allow us to ask multiple answers on the same
        # query. If this flag is set to false, we will ask the answer one
        # at a time, despite the feature.
        # Default is true. 
        self.enableMultipleAnswer = True
    
    def completeIt(self, multipleAnswer:int, prompt:str) -> list[str] :
        if self.DEBUG: print(">>> PROMPT:\n" + prompt)

        # some models limit the number of multiple-answers it could give:
        maxMultipleAnswers = multipleAnswer
        if self.model.startswith("o1") :
            maxMultipleAnswers = 8
        if self.enableMultipleAnswer == False:
            maxMultipleAnswers = 1
        
        # some models do not allow temperature to be set!!
        xtemperature = 0.7
        if self.model.startswith("o1") :
            xtemperature = 1
        
        remainToDo = multipleAnswer
        responses = []
        while remainToDo > 0:
            numberOfAnswersToAsk = min(remainToDo,maxMultipleAnswers)
            if self.DEBUG: 
                print(f">>> asking {numberOfAnswersToAsk} answers")
            completion = self.client.chat.completions.create(
                model = self.model,
                temperature = xtemperature,
                n = numberOfAnswersToAsk,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                    ]
                )
            N = min(numberOfAnswersToAsk, len(completion.choices))
            responses = responses + [ completion.choices[k].message.content for k in range(N) ]
            remainToDo = remainToDo - numberOfAnswersToAsk

        if self.DEBUG: 
            for k in range(len(responses)):
                print(f">>> raw response {k}:\n {responses[k]}")
        return responses



if __name__ == '__main__':
    openai_api_key = os.environ.get('OPENAI_API_KEY') 
    openAIclient = OpenAI(api_key=openai_api_key)
    modelId = "gpt-3.5-turbo"
    #modelId ="gpt-4-turbo"  --->  this model is expensive!
    #modelId ="gpt-4o" 
    #modelId ="o1-preview"  #--> n should be <= 8
    #modelId ="o3-mini"  --> not recognized (yet?)

    myAIclient = MyOpenAIClient(openAIclient,modelId)
    myAIclient.DEBUG = True
    #myAIclient.enableMultipleAnswer = False

    ROOT = os.path.dirname(os.path.abspath(__file__))
    #dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "mini.json")
    dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "HEx-compact.json")
    #dataset = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data", "simple-specs.json")

    generate_results(myAIclient,
                     dataset, 
                     specificProblem = "HE21" ,
                     experimentName = "bla",     
                     enableEvaluation = True, 
                     allowMultipleAnswers = 3,
                     prompt_type = "usePrgDesc"
                     #prompt_type="cot2"
                     )
    
 
    