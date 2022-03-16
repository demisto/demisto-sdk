#!/bin/sh
set -e
mkdir -p /devwork/
cd /devwork
chown -R :4000 /devwork/
chmod -R 775 /devwork
exec_pwsh_command() {
    pwsh -Command $@
    if [ $? != 0 ]; then
        exit 1
    fi
}
exec_pwsh_command Set-PSRepository -name PSGallery -installationpolicy trusted -ErrorAction Stop
exec_pwsh_command Install-Module -Name Pester -Scope AllUsers -Force -ErrorAction Stop
exec_pwsh_command Invoke-Pester -?
exec_pwsh_command Install-Module -Name PSScriptAnalyzer -Scope AllUsers -Force -ErrorAction Stop
exec_pwsh_command Invoke-ScriptAnalyzer -?
