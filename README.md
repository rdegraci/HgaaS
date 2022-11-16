# HgaaS
Mercury as a Service


## Idea

Mercury as a Service is a web-based resource for communication thru programming.

Astrologically:
```
Mercury uses its clever intellect and relentless curiosity to analyze, sort, and classify, helping us synthesize and articulate complex ideas.
```

## Implementation

HgaaS provides web-based syntax-highlighted code editors, a way to explore and discover current modules, and a way to view process logs. 

HgaaS provides a process-manager that restarts the process when files are modified, restarts the process when it crashes, restarts the process 
periodically (for cases where the process hangs), and produces rotating log files.

## Blowhardiness

HgaaS is a tool that will improve human-human relations through programming languages and shared simulative and productive environments. 

HgaaS is the future of math. 

Mercury 4eva. 

## Running Locally

- Clone the repo and `cd` into it
  ```bash
  git clone https://github.com/bodygenre/HgaaS.git && cd "$(basename "$_" .git)"
  ```

- (optional) Create a Python virtual environment and activate it
  ```bash
  python -m venv .env && source "$_/bin/activate"
  ```

- Install dependencies
  ```bash
  pip install -r requirements.txt
  ```

- Copy the template file and name it `hgaas.json`
  ```bash
  cp config.json.template hgaas.json
  ```

- (optional) Edit `hgaas.json` to your liking and save it
  ```bash
  $EDITOR hgaas.json
  ```

- Summon Mercury in the current directory
  ```bash
  python server.py .
  ```