## spell-check
Check the spelling in .md and .yml files.

**Use-Cases**
Used to check for misspelled words in .md files such as README and integration descriptions also in .yml file such as integrations, scripts and playbooks.

**Arguments**:
* **-i, --input**
The path to the file to check.
* **--no-camel-case**
Whether to check CamelCase words.
* **--known-words**
The path to a file containing additional known words.
* **--always-true**
Whether to fail the command if misspelled words are found.
* **--expand-dictionary**
Whether to expand the base dictionary to include more words - will download 'brown' corpus from nltk package.

**Examples**
1. `demisto-sdk spell-check -i ~/Integrations/integration-MyInt.yml --no-camel-case`
This will check the spelling in the integration file given and will treat camel case words as misspelled words.

2. `demisto-sdk split-yml -i Packs/MyPack/Scripts --expand-dictionary`
This will spell check all eligible files under the `Packs/MyPack/Scripts` directory. This will also download and use the `brown` corpus from the `nltk` package.

3. `demisto-sdk split-yml -i ~/Integrations/MyIntegration/README.md --known-words ~/Integrations/additional_words.txt`
This will spell check the given readme file as well as expand the known words with the words found in the `additional_words.txt` file.
