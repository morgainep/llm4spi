import getopt
import json
import sys
import os
import shutil
import tempfile
from pathlib import Path

# import from llm4spi code
sys.path.append('../llm4spi')
from data import read_problems

import subprocess
from testSuiteManager import extractTests, getInputVectorFromTestFunction, checkPreCondition, \
    computePrograOutput, checkPostCondition, removeDuplicatedTCs

'''
For a given benchmark, generate test cases using pynguin
'''

# global parameters

options = [
    ("benchmarkDir", "The folder where the benchmark is located. If not specified: ../../llm4spiDatasets/data"),
    ("benchmark", "The name of the benchmark-file to target, e.g. simplespecs.json. Mandatory."),
    ("testFolder", "The folder where tests are saved. If not specified: ./testFolder"),
    ("pynguinTimeBudget", "Maximum time (in seconds) used by Pynguin for generating the tests for a task. If not specified: 180"),
    ("algorithm", "Test generation algorithm. If not specified: DYNAMOSA"),
]

helpMessage = "Usage\n"
helpMessage += "python testCaseGenerator.py [--option=arg]*\n"
helpMessage += "   Options:\n"
for o in options:
   helpMessage +=  f"   --{o[0]} : {o[1]}\n"

version = "0.0.1"
welcomeMessage = "Running testCaseGenerator v"+version+"\n"

poodleConfigFile = "poodle_config.py"
ROOT = os.path.dirname(os.path.abspath(__file__))
poodleConfigFilePath = os.path.join(ROOT, poodleConfigFile)

# help function to create a folder
def createTestFolder(testFolderPath: str) -> bool:

    # check if testFolderPath already exists
    if os.path.exists(testFolderPath):
        if os.path.isdir(testFolderPath):
            print(f"Folder '{testFolderPath}' already exists.")
            return False
        else:
            print(f"Error: '{testFolderPath}' already exists but is not a folder.")
            return False

    # build folder
    try:
        os.makedirs(testFolderPath, exist_ok=True)
        return True
    except OSError as e:
        print(f"Error creating folder {testFolderPath}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while creating {testFolderPath}")
        return False


# apply patch patchStr to function funStr and returns patched function as a string
def applyPatch(funStr: str, patchStr: str) -> str:
    patchedFunStr = ""
    # create tmp folder

    tempDir = tempfile.TemporaryDirectory()
    #print(tempDir.name)
    # use temp_dir, and when done:
    funStrPath = os.path.join(tempDir.name,"prog.py")
    patchStrPath = os.path.join(tempDir.name, "patch.diff")
    with open(funStrPath, "w") as f:
        f.write(funStr)
    with open(patchStrPath, "w") as f:
        f.write(patchStr)

    # apply pacth
    patchedFunPath = os.path.join(tempDir.name,"progPatched.py")

    patchCommand = [
        "patch",
        "-o", patchedFunPath,
        funStrPath,
        patchStrPath
    ]


    try:
        process_result = subprocess.run(
            patchCommand,
            capture_output=True,
            text=True,
            check=True,
            cwd=tempDir.name
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: Patch execution failed with exit code {e.returncode}")
        return ""
    except FileNotFoundError:
        print("Error: Patch command not found. Make sure Patch is installed and in your PATH.")
        return ""

    # read patched
    try:
        with open(patchedFunPath, "r") as f:
            patchedFunStr = f.read()
            # print(patchedFunStr)
    except Exception as e:
        print(f"Unexpected error occurred in reading patched file: {e}")
        return ""

    return  patchedFunStr


# The function run poodle, generate test cases with pynguin and returns a list of string contanining the generated tests
def runPoodle(workingFolder: str, moduleName: str, program: str, searchTimePynguin: int, algorithmPynguin : str ) -> [str]:

    # poodle --only HE0.py . -vv --html report_html --json report.json
    generateTests = []

    testFolder = os.path.join(workingFolder, moduleName)
    configFile = os.path.join(testFolder, poodleConfigFile)
    jsonOutFile = "report.json"
    try:
        shutil.copy(poodleConfigFilePath,configFile)
    except Exception as e:
        print(f"Unexpected error occurred in copying poodle config: {e}")
        return []

    poodleCommand = [
        "poodle",
        "--only" , moduleName + ".py",
        "--html",  "report_poodle",
        "--json", jsonOutFile,
        "."
    ]

    # print(f"{poodleCommand}")
    # run
    try:
        process_result = subprocess.run(
            poodleCommand,
            capture_output=True,
            text=True,
            check=True,
            cwd=testFolder
        )
    except subprocess.CalledProcessError as e:
        print(f"Error: Poodle execution failed with exit code {e.returncode}")
        return []
    except FileNotFoundError:
        print("Error: Poodle command not found. Make sure Poodle is installed and in your PATH.")
        return []

    # read the json generated by poodle
    jsonOutPath = os.path.join(testFolder,jsonOutFile)
    try:
        with open(jsonOutPath, 'r') as file:
            poodleData = json.load(file)
    except:
        print(f"Error: Cannot read json file {jsonOutPath}.")
        return []

    mutantTrials = poodleData['mutant_trials']
    # iterate over mutations
    # All?
    print(f"Found {len(mutantTrials)} mutations")
    for i in range(len(mutantTrials)):
        # print(f"Mutatio {i} of {moduleName}")
        mutPath = os.path.join(testFolder,moduleName+"_mut"+str(i))
        createTestFolderOk = createTestFolder(mutPath)
        if not createTestFolderOk:
            print(f"Error: Cannot create mutation folder {mutPath}.")
            return []
        # extract mutation patch
        mut = mutantTrials[i]['mutant']['unified_diff']
        programMut = applyPatch(program,mut)
        if programMut != "":
            # print(f"Mutation is valid")
            # run pynguin on the mutated code
            pynguinTests = runPynguin(mutPath, programMut, moduleName, searchTimePynguin, algorithmPynguin)
            generateTests.append(pynguinTests)
        # else:
        #    print(f"Mutation is not valid")

    return generateTests




# function to run pynguin
def runPynguin(workingFolder: str, functionToTest: str, moduleName: str, searchTime: int, algorithm : str) -> str or None:

    try:

       testFolder =  os.path.join(workingFolder, moduleName)
       createTestFolderOk = createTestFolder(testFolder)

       if (not createTestFolderOk):
           print(f"Cannot create test folder {testFolder}. Quitting.")
           sys.exit(6)

       sutFilePath = os.path.join(testFolder, f"{moduleName}.py")
       testOutputDir = os.path.join(testFolder, "report")

       # save function to file
       with open(sutFilePath, "w") as f:
           f.write(functionToTest)

       # build Pynguin command
       pynguinCommand = [
           "pynguin",
           "--project-path", testFolder,
           "--module-name", moduleName,
           "--output-path", testFolder,
           "--report-dir", testOutputDir,
           "--maximum_search_time", searchTime,
           "--original_type_weight", "100",
           "--type4py_weight", "1",
           "--type_tracing_weight", "1",
           "--algorithm", algorithm,
           "--coverage-metrics", "BRANCH",
           "--assertion-generation", "NONE",
           "--maximum-iterations", "1000",
           "--create-coverage-report", "True",
           "--post_process", "True"
       ]

       # print(f"{pynguinCommand}")
       # run
       try:
           process_result = subprocess.run(
               pynguinCommand,
               capture_output=True,
               text=True,
               check=True
           )
       except subprocess.CalledProcessError as e:
           print(f"Error: Pynguin execution failed with exit code {e.returncode}")
           return None
       except FileNotFoundError:
           print("Error: Pynguin command not found. Make sure Pynguin is installed and in your PATH.")
           return None

       # Find and read the generated test file
       pathToTestFile = os.path.join(testFolder, f"test_{moduleName}.py")

       if not os.path.exists(pathToTestFile):
           print(f"Error: Test file not found at {pathToTestFile}. Pynguin might have failed to generate tests.")
           return None
       with open(pathToTestFile, "r") as test_file:
           test_suite_code = test_file.read()
       # print(f"Successfully created test suite for {moduleName}.")
       return test_suite_code

    except Exception as e:
        print(f"Unexpected exception: {e}")
        return None

def parsePynguinTestCode(testsCode: str, task: str, tasks: dict) -> dict:

    outTests = {}
    positivePreTests = []
    negativePreTests = []
    positivePostTests = []
    negativePostTests = []

    for testCase in testsCode:
        # extract the input of the test cases and check for pre-conditions
        testSuiteVector = getInputVectorFromTestFunction(testCase, task)

        for tc in testSuiteVector:
            # filter by precondition
            checkPre = True
            if tasks[task]["pre_condition_solution"] != "":
                # check precondition
                checkPre = checkPreCondition(tc, tasks[task]["pre_condition_solution"])
                # print(f"Pre check {checkPre}")
            # if checkPre is None, something went wrong when running precondition. Ignore test case
            if checkPre == None:
                continue
            elif not checkPre:
                negativePreTests.append(removeDuplicatedTCs(tc))
                continue

            # tc passes pre condition

            # add sut output
            tcWithOutput = computePrograOutput(tc, tasks[task]["program"])
            # if program return None, continue
            if tcWithOutput == None:
                continue
            # tc has been extended with output successfully
            # check procondition
            postCheck = checkPostCondition(tcWithOutput, tasks[task]["post_condition_solution"])

            # print(f"Post check {postCheck}")
            if postCheck == None:
                continue
            elif postCheck:
                positivePostTests.append(removeDuplicatedTCs(tcWithOutput))
            else:
                print(f"Found negative post")
                negativePostTests.append(removeDuplicatedTCs(tcWithOutput))
                #raise RuntimeError(f"Test case {tcWithOutput} fails post-condition check for task {task}")


    outTests["positivePreTests"] = positivePreTests
    outTests["negativePreTests"] = negativePreTests
    outTests["positivePostTests"] = positivePostTests
    outTests["negativePostTests"] = negativePostTests
    return  outTests

def generateTestCases(parameters):

    # set default values for input
    benchmarkDir_ = os.path.join(ROOT, "..", "..", "llm4spiDatasets", "data")
    benchmark_ = None
    testFolder_ = os.path.join(ROOT, "testFolder")
    pynguinTimeBudget_ = 180
    algorithm_ = "DYNAMOSA"
    # parse parameters
    try:
        opts, args = getopt.getopt(parameters, "h", [o[0] + "=" for o in options])
    except getopt.GetoptError:
        print(helpMessage)
        sys.exit(134)  # ENOTSUP	134	Not supported parameter or option
    for opt, arg in opts:
        match opt:
            case "-h":  # print help
                print(helpMessage)
                sys.exit(0)
            case "--benchmark":
                benchmark_ = arg
            case "--benchmarkDir":
                benchmarkDir_ = arg
            case "--testFolder":
                testFolder_ = arg
            case "--pynguinTimeBudget":
                pynguinTimeBudget_ = arg
            case "--algorithm":
                algorithm_ = arg
            case _:  # default print help and exit
                print(helpMessage)
                sys.exit(0)

    # create test folder
    createFolderOk = createTestFolder(testFolder_)

    if createFolderOk:
        # load the benchmark
        benchmarkFile = os.path.join(benchmarkDir_, benchmark_)
        tasks = read_problems(benchmarkFile)

        # set python PYNGUIN_DANGER_AWARE vairable
        os.environ["PYNGUIN_DANGER_AWARE"] = "1"

        allTests = []

        for task in tasks:

            posPreTestsTask = []
            negPreTestsTask = []
            posPostTestsTask = []
            negPostTestsTask = []

            taskTests = {}
            taskTests["problemId"] = task

            print("Processing task " + task)

            # generate the test suite for the current task
            pynguinTests = runPynguin(testFolder_, tasks[task]["program"], task, pynguinTimeBudget_, algorithm_)
            if pynguinTests == None:
                print(f"Error in processing task {task}")
                continue

            # extract the code of the test cases
            testsCode = extractTests(pynguinTests)
            taskTests["tests_code"] = testsCode

            # get valid tests
            print("Run pynguin on " + task)
            validPyTests = parsePynguinTestCode(testsCode, task, tasks)

            posPreTestsTask.append(validPyTests['positivePreTests'])
            negPreTestsTask.append(validPyTests['negativePreTests'])
            posPostTestsTask.append(validPyTests['positivePostTests'])

            if len(validPyTests['negativePostTests']) > 0:
                print(f"Error: pynguin generates negative post tests")


            # run poodle in the generated folder
            print("Run poodle on " + task)
            poodleTests = runPoodle(testFolder_, task,  tasks[task]["program"], pynguinTimeBudget_, algorithm_)
            print("Check poodle tests on " + task)
            for pt in poodleTests:
                tc = extractTests(pt)
                validPT = parsePynguinTestCode(tc, task, tasks)
                posPreTestsTask.append(validPT['positivePreTests'])
                negPreTestsTask.append(validPT['negativePreTests'])
                posPostTestsTask.append(validPT['positivePostTests'])
                negPostTestsTask.append(validPT['negativePostTests'])

            taskTests['positivePreTests'] = str(removeDuplicatedTCs(posPreTestsTask))
            taskTests['negativePreTests'] = str(removeDuplicatedTCs(negPreTestsTask))
            taskTests['positivePostTests'] = str(removeDuplicatedTCs(posPostTestsTask))
            taskTests['negativePostTests'] = str(removeDuplicatedTCs(negPostTestsTask))

            allTests.append(taskTests)
        # save in a json file all the generated tests
        generatedTestFile = os.path.join(testFolder_, "generatedTests.json")
        with open(generatedTestFile, "w") as gtf:
            json.dump(allTests, gtf)

    else:
        print(f"Cannot create test folder {testFolder_}. Quitting.")
        sys.exit(6)


if __name__ == "__main__":

    # print welcome message
    print(welcomeMessage)

    # read parameters
    parameters = sys.argv[1:]

    # run test cases generation
    generateTestCases(parameters)

