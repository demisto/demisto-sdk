> This is a temporary file to track changes to the download command while working on the PR.
> This file should be removed before merging the PR (and should be summarized within the CHANGELOG.md file)

* A rewrite for the **download** command, with many improvements and fixes, including:
  * Optimizations, reducing the runtime & CPU usage by a significant amount when there are many custom content items on the server.
  * Improved error handling & messages, logs, and documentation (`demisto-sdk download --help`) for the command to be more descriptive.
  * Fixed an issue where custom PowerShell-based integrations and automations would not download properly.
  * Fixed an issue where names of the following custom content items would not be replaced from UUIDs:
    * Classifiers
    * Dashboards
    * Indicator Types
    * Reports
    * Widgets
  * Fixed an issue where the download would fail when using the '-r' / '--regex' flag if there are multiple custom content items on the server using the same name.
  * Fixed an issue where Integrations / Automations with a `.` in their name would not be named correctly (For example: `Test v1.1.py` would be renamed to `Test v1.py`)

**Note:** Due to some changes, playbooks might be formatted a bit differently than before when downloaded from the server. The playbooks should however function the same, and just not have
