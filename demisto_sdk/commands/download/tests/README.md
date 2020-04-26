## What to do when tests environment is broken
* Delete `demisto_sdk/commands/download/tests/tests_data`
* Delete `demisto_sdk/commands/download/tests/tests_env`
* Copy `demisto_sdk/commands/download/tests_backup/tests_data` to `demisto_sdk/commands/download/tests`
* Copy `demisto_sdk/commands/download/tests_backup/tests_env` to `demisto_sdk/commands/download/tests`
