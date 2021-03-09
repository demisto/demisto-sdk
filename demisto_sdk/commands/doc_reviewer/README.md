## doc-review
Check the spelling in .md and .yml files as well as review release notes.

**Use-Cases**
 - Used to check for misspelled words in .md files such as README and integration descriptions also in .yml file such as integrations, scripts and playbooks.
 - Performs a basic documentation review on release notes.

**Arguments**:
* **-i, --input**
The path to the file to check.
* **-g**, **--use-git**
Use git to identify the relevant changed files. Will be used by default if '-i' and '--templates' are not set.
* **--prev-ver**
The branch against which changes will be detected if '-g' flag is set. Default is 'demisto/master'.
* **--no-camel-case**
Whether to check CamelCase words.
* **--known-words**
The path to a file containing additional known words.
* **--always-true**
Whether to fail the command if misspelled words are found.
* **--expand-dictionary**
Whether to expand the base dictionary to include more words - will download 'brown' and 'webtext' corpora from nltk package.
* **--templates**
Whether to print release notes templates.
* **-rn**, **--release-notes**
Will run only on release notes files.

**Examples**
1. `demisto-sdk doc-review -i ~/Integrations/integration-MyInt.yml --no-camel-case`
This will check the spelling in the integration file given and will treat camel case words as misspelled words.

2. `demisto-sdk doc-review -i Packs/MyPack/Scripts --expand-dictionary`
This will spell check all eligible files under the `Packs/MyPack/Scripts` directory. This will also download and use the `brown` and `webtext` corpora from the `nltk` package.

3. `demisto-sdk doc-review -i ~/Integrations/MyIntegration/README.md --known-words ~/Integrations/additional_words.txt`
This will spell check the given readme file as well as expand the known words with the words found in the `additional_words.txt` file.

4. `demisto-sdk doc-review --templates`
This will print the documentation templates examples.

5. `demisto-sdk doc-review --prev-ver myRemote/master -rn`
This will perform a doc review on all the release notes that were changed (added or modified) when compared to 'myRemote/master' using git.
