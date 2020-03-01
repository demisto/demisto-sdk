### Lint

Run lintings (flake8, mypy, pylint, bandit, vulture) and pytest.
pylint and pytest will run within all the docker images of an integration/script.
Meant to be used with integrations/scripts that use the folder (package) structure.

The appropriate docker images for the integration/script will be used to execute the pytest and pylint checks.

**Use Cases**
This command is used to make sure the code stands up to the python standards, prevents bugs and runs unit tests to
make sure the code works as intended.

**Arguments**:
* **-d DIR, --dir DIR**
  Specify directory of integration/script. Also supports several direcories as a CSV (default: None)
* **--no-pylint**
  Do NOT run pylint linter (default: False)
* **--no-mypy**
  Do NOT run mypy static type checking (default: False)
* **--no-flake8**
  Do NOT run flake8 linter (default: False)
* **--no-bandit**
  Do NOT run bandit linter (default: False)
* **--no-vulture**
  Do NOT run vulture linter (default: False)
* **--no-test**
  Do NOT test (skip pytest) (default: False)
* **-r, --root**
  Run pytest container with root user (default: False)
* **-p, --parallel**
  Run tests in parallel (default: False)
* **-m, --max-workers**
  The max workers to use in a parallel run (default: 10)
* **-g, --git**
  Run only on packages that changes between the current branch and content repo's origin/master branch (default: False)
* **-a, --run-all-tests**
  Run lint on all directories in content repo (default: False)
* **-k, --keep-container**
  Keep the test container (default: False)
* **-v, --verbose**
  Verbose output (default: False)
* **--outfile** Specify a file path to save failing package list. (default: None)
* **--cpu-num CPU_NUM**
  Number of CPUs to run pytest on (can set to `auto` for automatic detection of the number of CPUs.) (default: 0)


**Examples**:
`demisto-sdk lint -d Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --no-mypy -p -m 2`
This will parallel run the linters, excluding mypy, on the python files inside the "Integrations/PaloAltoNetworks_XDR" and "Scripts/HelloWorldScript" directories, using 2 workers (threads).
<br/><br/>

`demisto-sdk lint -a -g`
This will run on all content repo's packaged and packed integrations and scripts and will activate the linting and tests only on the directories which had their files changed in comparison with content origin/master branch.
<br/><br/>

`demisto-sdk lint -d Interagtions/HelloWorld -v --no-bandit --no-flake8 --cpu-num auto`
This will run the linters, excluding bandit and flake8, on "Integrations/HelloWorld" and give additional details on the run itself as well as any failures detected.
Also this will check the amount of CPU's available to run pytest on and use them.
<br/><br/>

`demisto-sdk lint -d Scripts/HelloWorldScript --no-pytest --no-pylint`
This will run only the linters (flake8, mypy, bandit, vulture) on "Scripts/HelloWorldScript".
<br/><br/>

`demisto-sdk lint -d Integrations/HelloWorld --no-mypy --no-flake8 --no-pytest -k -r`
This will run only pylint and pytest on "Integrations/HelloWorld" using the root user for the pytest and will also keep the test container with the docker image after the operation is over.

`demisto-sdk lint -g --outfile ~/failures.txt`
This indicates lint runs only on changed packages from content repo's 'origin/master' branch and saves the failed packages to failures.txt file.


**Notes**
Vulture reports dead code with confidence level of 100% by default.
The minimum confidence level can be set by changing the environment variable `VULTURE_MIN_CONFIDENCE_LEVEL`, i.e. `export VULTURE_MIN_CONFIDENCE_LEVEL=60`.
