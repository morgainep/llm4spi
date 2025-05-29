# Project: using LLMs to write SPises

Since LLMs are so smart, we wonder how good they are for generating 'formal' specifications. Or at least, specifications that can be executed so we can actually use them for checking the inputs and outputs of programs under test.

This project provides a script for assessing LLMs ability to extract formal pre- and post-conditions from a program's description. We can consider both commercial LLMs like OpenAI GPTs as well open source LLMs.
Note that this project only provides the assessment tool. To actually do the assessment you also need a benchmarking dataset as the input for the tool. A tiny demo-dataset is provided in the project. Actual datasets are to be provided separately.

#### Some funny examples

This are just samples of manual interactions with LLMs we found somewhat refreshing...

_Give a Python program `Postcondition(x,y,z)` that checks whether the sum of x and y is zero or equal to z_

Answer by Orca-mini-3B: 😅

```python
Postcondition(x,y,z):
     if x + y == 0 or x - y == 0 or z - x == 0:
     return True
     else:
     return False
```

_Give a Python program `Postcondition(joke:str)` that checks whether the joke is funny._ 😉

Answer by OpenAI's GPT:

```python
def Postcondition(joke: str) -> bool:
    # Use VADER for a basic sentiment analysis approach
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(joke)

    # Consider a joke "funny" if it has a positive sentiment
    if sentiment['pos'] > sentiment['neg']:
        return True
    return False

# Example usage
joke = "Why don't scientists trust atoms? Because they make up everything!"
print(Postcondition(joke))  # Output: True
```

#### Some old results

  |  | simple-specs-40 | HEx-26 |
  |--|----------|----|
  | GPT 4o          | 92.5%  |
  | GPT 4 turbo          | 87.5%  |
  | GPT 3.5 turbo        | 85%  | 57% (base-test1) / 73% |
  | codellama-7b-instruct.Q8_0           | 27.5% (using prg-desc) / 35%  | 15% |
  | codellama-13b-instruct.Q6_K          | 32.5%, but slow  |
  | codellama-13b-instruct.Q4_0 | 30% |
  | Meta-Llama-3-8B-Instruct.Q4_0 | 35% (using prg-desc) / 35%  |
  | Llama-3-15b-Instruct-GLUED.Q6_K | 32.5%, but very slow |
  | Meta-Llama-3-8B-Instruct (Groq, possibly 16f) |  | 48% using prg-desc |
  | Meta-Llama-3-70B-Instruct (Groq, possibly 16f) |  | 65.5% using prg-desc |
  | mistral-7b-instruct-v0.2.Q8_0      | 27.5%  |
  | orca-2-13b.Q4_0   | 15%  |
  | wizardcoder-python-13b-v1.0.Q4_K_M | 10%, very slow |
  | gemma2-9b-it (Groq, possibly 16f) | 48% using prg-desc |



## Required Python and Python packages

* Require Python 3.12
* For package dependencies, see `requirements.txt`. In any case, pip install the following packages:
  * To use OpenAI models: `openai`
  * To use Gpt4All: `gpt4all`
  * To use Hugging Face models: `huggingface-hub`
  * To use Google models: `google-genai`
  * To use open models compatible with llama-cpp: `llama-cpp-python`

## Datasets

Except for a tiny demo-dataset, this project does not come with an actual dataset. Actual datasets are managed in a separate project/s.


A **dataset** is essentially a set of programming **problems**/tasks. Each problem is a tuple (_D,F,pre,post,T_) where _D_ is a natural language description of some program (describing what functionality the program is supposed to provide), _F_ is a Python implementation of _D_, pre is a solution pre-condition of _F_, post is a solution post-condition of _F_, and _T_ is a set of tests. The task for an LLM is to propose a _pre'_ and _post'_, given the description _D_. The proposals are correct if they are equivalent to the solutions pre/post, validated by testing using _T_.

A compatible dataset is expected to be provided as a json-file of a specific structure. As an example: see the file `mini.json`.


## Running the assessment tool

Go to the directory `.\llm4spi`, you can run the assessment tool from the command line by running the script `clispi.py`:

   `> python clispi.py -h` will show available options.

Example:

   `> python clispi.py --provider=openAI --model=gpt3.5 --experimentName=xxx --benchmarkDir=../ --benchmark=mini`

This will run the assessment of openAI GPT3.5 LLM against the benchmark called _mini_. This assumes a dataset named `mini.json` exists in the directory specified by the option `--benchmarkDir`. For every problem in this _mini_ dataset, the assessment script will send a prompt to the API of OpenAI, asking for proposal pre- and post-conditions.

The assessment tool sees LLMs to be provided by a provider, which could be remote or local. Internally, the choice of the provider determines the specific interface that the tool uses to interact with the LLM (each LLM may require a specific interface to be interacted with).
The option `--provider` specifies which provider is to be used.

Implemented remote providers: `openAI`, `groq`, `anthropic`, and `gemini`.
When using an LLM provided by these providers, you would need an API-key. You can check the information at the provider website on how to get such an API-key. Before running the assessment tool, set the API-key to an environment variable of your command line shell.
For OpenAI, set the key in the env-variable `OPENAI_API_KEY`. Similarly, to use Anthropic's models set your Anthropic API-key in the env-var `ANTHROPIC_API_KEY`.


The option `--model` specifies the name/id that identifies the specific model/LLM that you want to use. This name only matters if the LLM is provided by a remote provider. The website of the provider should have information of models they provide and their names. For local LLM, the name does not matter, but useful to identify the generated outputs.

Implemented local provider:
 `gpt4all`, and  `llamacpp`. For these providers you don't need API key. You do need to set the path to the local model to use. E.g. if you use a GPT4All-compatible model, use the option `--gpt4all_localModelPath`. If you use a llama-cpp compatible model, set the path with the option `--llamacpp_localModelPath`.

Use the option `--allowMultipleAnswers` if you want to obtain multiple proposals per problem.

When the assessment finishes, a summary will be printed to the console, and several files will be generated in the directory `./results`. There will be a csv file containing a summary of the assessment, and also a json file containing raw responses from the LLM as well as distilled responses.

  * `xxx_summary_prompttype_timestamp.txt` : overall summary of the assessment.
  * `xxx_evaluation_promptype_timestamp.csv`: per-problem/task result of the assessment.
  * `xxx_all_prompttype_timestamp.json`: contains the raw data produced by the evaluation. It contains the raw responses from the LLMs as well as the proposal-code (Python) extracted from these raw responses. The json also contains the result of every test-case run used to validate each proposal from the LLM.
  For convenience, the expected/reference result of every test-case is also included.


## Adding more tests (experimental feature)

A compatible dataset should already contain test-suites for each problem in the dataset. More tests can be added by editing the json-file that contains the dataset, and the re-running the assessment tool (this will query the LLM anew).

You can also write the tests in a separate json-file. Essentially, every test is represented by a list of inputs. In the file we specify extra tests to run for every problem. You can then use the function `collectTestResults` provided in `postmortem1.py`. Go to the directory `.\llm4spi`, do:

`python -c 'from postmortem1 import collectTestResults;
collectTestResults(dataset,idir,additionalTests,odir)'`

   * _dataset_ : path to the dataset
   * _idir_ : directory that should contain collected raw outputs of the analysis tool. These are json-files of the form `xxx_all_prompttype_timestamp.json`.
   * _additionalTests_ : path to the json-file containing additional tests.
   * _odir_ : where the results of all test runs will be placed (these include tests that are already in the dataset plus the extra ones).

The function `collectTestResults` does not query the LLM anew. Instead, it justs reeuse previously produced proposals stored in the xxx_all_yyy.json files.

The produced file: `extendedResults_xxx_all_yyy.json`.

## Other notes

#### Some notes on using GPT4All

You can use a [Docker-image with GPT4All installed](https://hub.docker.com/r/morgaine/llm4spi). The image has:

* Ubuntu 22-04
* Python 3.12 installed
* NVIDIA Container Toolkit installed
* Vulkan SDK installed
* GPT4All installed (as a Python package)
