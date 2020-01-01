### Lint

Run lintings (flake8, mypy, pylint, bandit) and pytest.
pylint and pytest will run within all the docker images of an integration/script. Meant to be used with integrations/scripts that use the folder (package) structure. Will lookup up what docker image to use and will setup the dev dependencies and file in the target folder.
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
* **--cpu-num CPU_NUM**
  Number of CPUs to run pytest on (can set to `auto` for automatic detection of the number of CPUs.) (default: 0)


**Examples**:
`demisto-sdk lint -d Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --no-mypy -p -m 2`
This will parallel run the linters, excluding mypy, on the python files inside the "Integrations/PaloAltoNetworks_XDR" and "Scripts/HelloWorldScript" directories, using 2 workers (threads).

`demisto-sdk lint -a -g`
This will run on all content repo's packaged and packed integrations and scripts and will activate the linting and tests only on the directories which had their files changed in comparison with content origin/master branch.

`demisto-sdk lint -d Interagtions/HelloWorld -v --no-bandit --no-flake8 --cpu-num auto`
This will run the linters, excluding bandit and flake8, on "Integrations/HelloWorld" and give additional details on the run itself as well as any failures detected.
Also this will check the amount of CPU's available to run pytest on and use them.

`demisto-sdk lint -d Scripts/HelloWorldScript --no-pytest --no-pylint`
This will run only the linters (flake8, mypy, bandit) on "Scripts/HelloWorldScript".

`demisto-sdk lint -d Integrations/HelloWorld --no-mypy --no-flake8 --no-pytest -k -r`
This will run only pylint and pytest on "Integrations/HelloWorld" using the root user for the pytest and will also keep the test container with the docker image after the operation is over.
