#!/bin/sh
mkdir -p /devwork/
cd /devwork
chown -R :4000 /devwork/
chmod -R 775 /devwork
pwsh -Command Set-PSRepository -name PSGallery -installationpolicy trusted -ErrorAction Stop
pwsh -Command Install-Module -Name Pester -Scope AllUsers -Force -ErrorAction Stop
pwsh -Command Install-Module -Name PSScriptAnalyzer -Scope AllUsers -Force -ErrorAction Stop
