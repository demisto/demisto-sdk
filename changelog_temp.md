> This is a temporary file to track changes to the download command while working on the PR.
> This file should be removed before merging the PR (and should be summarized within the CHANGELOG.md file)

// A comment about a big optimization for the download command, improving the runtime by a lot
* A rewrite for the **download** command, with a lot of improvements, including:
  * Optimizations, reducing the runtime & CPU usage by a significant amount when there are many custom content items on the server.
  * Improve error message, logs, and documentations (--help) for the command.
  * Fix an issue where custom PowerShell-based scripts and automations would not download properly.
  * Fix an issue where names of custom indicator types would not be detected properly, causing the ID to be used instead as their name.
  * Fix an issue where the download would fail if using the '-r' / '--regex' flag when there are different custom content items using the same name.
