## doc-review

### Overview
Check the spelling in .md and .yml files as well as review release notes.

**Use-Cases**
 - Used to check for misspelled words in .md files such as README and integration descriptions also in .yml file such as integrations, scripts and playbooks.
 - Performs a basic documentation review on release notes.

### Options
* **-i, --input**
Path to the file to check.
* **-g**, **--use-git**
Use git to identify the relevant changed files. Will be used by default if '-i' and '--templates' are not set.
* **--prev-ver**
The branch against which changes are detected if `-g` flag is set. Default is 'demisto/master'.
* **--no-camel-case**
Whether to run spell check on words in CamelCase.
* **--known-words**
Path to a file containing a list of known words.
* **--always-true**
Whether the command should fail if misspelled words are found.
* **--expand-dictionary**
Whether to expand the base dictionary to include more words. If this option is used, it will download `brown` and `webtext` corpora from nltk package
* **--templates**
Whether to print release notes templates.
* **-rn**, **--release-notes**
Run only on release notes files.
* **-xs**, **--xsoar-only**
Run only on files from XSOAR-supported Packs.
* **-pkw/-spkw**, **--use-packs-known-words/--skip-packs-known-words**
Will find and load the known_words file from the pack. To use this option make sure you are running from the content directory.

**Examples**
1. `demisto-sdk doc-review -i ~/Integrations/integration-MyInt.yml --no-camel-case`
Checks the spelling in the given integration file and treats camel case words as misspelled words.

2. `demisto-sdk doc-review -i Packs/MyPack/Scripts --expand-dictionary`
Spell checks all eligible files under the `Packs/MyPack/Scripts` directory. Also downloads and uses the `brown` and `webtext` corpora from the `nltk` package.

3. `demisto-sdk doc-review -i ~/Integrations/MyIntegration/README.md --known-words ~/Integrations/additional_words.txt`
Spell checks the given `README.md` file as well as expands the known words with the word list found in the `additional_words.txt` file.

4. `demisto-sdk doc-review --templates`
Prints the documentation template examples.

5. `demisto-sdk doc-review --prev-ver myRemote/master -rn`
Performs a documentation review on all the release notes that were changed (added or modified) when compared to 'myRemote/master' using git.
