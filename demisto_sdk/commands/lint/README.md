### Lint

  Lint command will perform:

  1. Package in host checks - flake8, bandit, mypy, vulture.

  2. Package in docker image checks -  pylint, pytest, powershell - test, powershell -
  analyze.

  Meant to be used with integrations/scripts that use the folder (package) structure. Will
  lookup up what docker image to use and will setup the dev dependencies and file in the target
  folder.

Options:
*  **-i, --input PATH**
    Specify directory(s) of integration/script
*  **-g, --git**
    Will run only on changed packages
*  **-a, --all-packs**
    Run lint on all directories in content repo
*  **-v, --verbose**
    Verbosity level -v / -vv / -vvv  [default: vv]
*  **-q, --quiet**
    Quiet output, only output results in the end
*  **-p, --parallel INTEGER RANGE**
    Run tests in parallel  [default: 1]
*  **--no-flake8**
    Do NOT run flake8 linter
*  **--no-bandit**
    Do NOT run bandit linter
*  **--no-xsoar-linter**
    Do NOT run XSOAR linter
*  **--no-mypy**
    Do NOT run mypy static type checking
*  **--no-vulture**
    Do NOT run vulture linter
*  **--no-pylint**
    Do NOT run pylint linter
*  **--no-test**
    Do NOT test (skip pytest)
*  **--no-pwsh-analyze**
    Do NOT run powershell analyze
*  **--no-pwsh-test**
    Do NOT run powershell test
*  **-kc, --keep-container**
    Keep the test container
*  **--prev-ver**
    Previous branch or SHA1 commit to run checks against
*  **--test-xml PATH**
    Path to store pytest xml results
*  **--failure-report PATH**
    Path to store failed packs report
*  **-lp, --log-path PATH**
    Path to store all levels of logs
*  **-j, --json-file**
    The JSON file path to which to output the command results
*  **--no-coverage**
    Do NOT report coverage
*  **--coverage-report**
    Specify directory for the coverage report files
*  **-dt, --docker-timeout**
    The timeout (in seconds) for requests done by the docker client


**Examples**:
---
`demisto-sdk lint -i Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --no-mypy`
Details:
1. lint and test check will execute on Packages `Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript`
2. Mypy check will not be execute.
3. coverage report will be printed.
---
`demisto-sdk lint -g -p 2`
1. lint and test check will execute on all Packages which are changed from `origin/master` and from in staging.
2. 2 Threads will be used inorder to preform the lint.
3. coverage report will be printed.
---
`demisto-sdk lint -i Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript --coverage-report coverage_report`
Details:
1. lint and test check will execute on Packages `Integrations/PaloAltoNetworks_XDR,Scripts/HellowWorldScript`
2. coverage report will be printed.
3. coverage report files will be exported to coverage_report dir.
---
