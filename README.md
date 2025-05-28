# Project: using LLMs to write SPises

Since LLMs are so smart, we wonder how good they are for generating 'formal' specifications. Or at least, specifications that can be executed so we can actually use them for checking the inputs and outputs of programs under test.

The project provides a framework for assessing LLMs ability to extract formal pre- and post-conditions from a program's description. We can consider both commercial LLMs like OpenAI GPTs as well open source LLMs.
Note that the project only provides the assessment framework. To actually do the assessment you also need a dataset containing problems/challenges. Such datasets are not provided here; they are provided separately.

Example prompt-1: _Give a Python program `Postcondition(x,y,z)` that checks whether the sum of x and y is zero or equal to z_

Answer by Orca-mini-3B: 😅

```python
Postcondition(x,y,z):
     if x + y == 0 or x - y == 0 or z - x == 0:
     return True
     else:
     return False
```

Example prompt-2: _Give a Python program `Postcondition(joke:str)` that checks whether the joke is funny._ 😉


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
* pip install the following packages:
  * To use OpenAI models: `openai`
  * To use Gpt4All: `gpt4all`
  * To use Hugging Face models: `huggingface-hub`
  * To use Google models: `google-genai`
  * To use open models compatible with llama-cpp: `llama-cpp-python`

## Datasets

This project does not come with a dataset. They are to be provided separately. A dataset is essentially a set of programming problems. Each problem is a tuple (D,F,pre,post,T) where D is a natural language description of some program (describing what functionality the program is supposed to provide), F is a Python implementation of D, pre is a solution pre-condition of F, post is a solution post-condition of F, and T is a set of tests. The task of an LLM is to propose a pre' and post', given the description D. The proposals are correct if they are equivalent to the solutions pre/post, validated by testing using T.

A dataset is expected to be provided as a json-file of a specific structure. As an xample: see the file `mini.json`.


## Usage

Go to the directory `llm4spi`, you can run the analysis tool from the command line by running the script `clispi.py`:

   `> python clispi.py -h` will show available options.

Example:

   `> python clispi.py --provider=openAI --model=gpt3.5 --benchmarkDir=../ --benchmark=mini`

This will run the evaluation of openAI GPT3.5 LLM against the benchmark called _mini_. This assumes a dataset named `mini.json` exists in the directory specified by the option `--benchmarkDir`. For every problem in this _mini_ dataset, the evaluation script will send a prompt to the API of OpenAI, asking for proposal pre- and post-conditions. Use the option `--allowMultipleAnswers` if you want to obtain multiple proposals per problem.

After the evaluation, a summary will be printed to the console, and several files will be generated in the directory `./results`. There will be a csv file containing a summary of the evaluation, and also a json file containing raw responses from the LLM as well as distilled responses.

To access OpenAI models you will need an API-key. Set the key in the env-variable `OPENAI_API_KEY`. Similarly, to use Anthropic's models you need an API-key as well; set it in the env-var `ANTHROPIC_API_KEY`.

Implemented providers: `openAI`, `gpt4all`, `groq`, `anthropic`, `gemini`, and  `llamacpp`.






## Other notes

#### Some notes on using GPT4All

You can use a [Docker-image with GPT4All installed](https://hub.docker.com/r/morgaine/llm4spi). The image has:

* Ubuntu 22-04
* Python 3.12 installed
* NVIDIA Container Toolkit installed
* Vulkan SDK installed
* GPT4All installed (as a Python package)
