#!/bin/sh

# Setup a container for dev testing for pwsh
#

# exit on errors
set -e

echo "setting up powershell testing image..."

if [ "${DEMISTO_LINT_UPDATE_CERTS}" = "yes" ]; then
    echo "updating ca certificates ..."
    update-ca-certificates
fi

pwsh -Command Set-PSRepository -name PSGallery -installationpolicy trusted
pwsh -Command 'Install-Module -Name Pester -Scope AllUsers; Invoke-Pester -? | Out-Null'
pwsh -Command 'Install-Module -Name PSScriptAnalyzer -Scope AllUsers; Invoke-ScriptAnalyzer -? | Out-Null'
