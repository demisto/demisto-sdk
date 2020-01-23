#!/bin/sh

# Run pylint and pytest in the current directory.
# Used by pkg_dev_test_tasks.py to run pylint and pytest
# inside a docker. Since this is meant to run inside a minimal docker
# image it uses sh and not bash. Additionally, script tries to keep it
# simply and not use any shell utilities that may be missing in a minimal docker.

# Env variables:
# PYLINT_FILES: file names to pass to pylint
# PYLINT_SKIP: if set will skip pylint
# PYTEST_SKIP: if set will skip pytest
# PYTEST_FAIL_NO_TESTS: if set will fail if no tests are defined
# CPU_NUM: number of CPUs to run tests on

pslint_return=0
if [ -z "${PS_LINT_SKIP}" ]; then
    echo "=============== Running PowerShell ScriptAnalayzer on files: ${PS_LINT_FILES} ==============="
    pwsh -Command "Invoke-ScriptAnalyzer -EnableExit -Path ${PS_LINT_FILES}"
    pslint_return=$?
    echo "PowerShell ScriptAnalayzer completed with status code: $pslint_return"
fi

if [ -z "${PS_TEST_SKIP}" ]; then
    echo ""
    echo "========= Running PowerShell Tests ==============="
    pwsh -Command Invoke-Pester -EnableExit
    pstest_return=$?
    echo "PowerShell Pester completed with status code: $pstest_return"
fi

if [ $pslint_return -ne 0 -o $pstest_return -ne 0 ]; then
    echo "=========== ERRORS FOUND ===========" 1>&2
    echo "lint/test returned errors. lint: [$pslint_return], test: [$pstest_return]" 1>&2
    echo "====================================" 1>&2
    exit 3
fi
