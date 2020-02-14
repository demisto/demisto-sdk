#!/bin/sh

# Run ScriptAnalayzer (lint) and Pester (test) in the current directory.
# inside a docker. Since this is meant to run inside a minimal docker
# image it uses sh and not bash. Additionally, script tries to keep it
# simply and not use any shell utilities that may be missing in a minimal docker.

# Env variables:
# PS_LINT_FILES: file names to pass to ScriptAnalayzer
# PS_LINT_SKIP: if set will skip lint
# PS_TEST_SKIP: if set will skip testing

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
