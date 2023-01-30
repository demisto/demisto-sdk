#!/bin/sh
set -e

echo "Running tests..."

pwsh Invoke-Pester -Configuration '@{Run=@{Exit=$true}; Output=@{Verbosity=\"Detailed\"}}'
