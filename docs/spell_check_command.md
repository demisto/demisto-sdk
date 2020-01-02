## Spell-check

**Checks spelling in a given .yml or .md file.**

### Use Cases
This command is used to check our user visible documents and descriptions for any misspelled words.

### Arguments
* **-p, --path**

  The path to the .yml or .md file to be checked.

* **--known-words**

  The path to a file of known words that won't raise an error.

### Notes
* A preset list known words can be found [here](https://github.com/demisto/demisto-sdk/tree/master/demisto_sdk/common/known_words.py).
* The command uses the [nltk](https://www.nltk.org/) package to enhance its dictionary - thus, running this command for the first time may take a minute to download the dictionary.

### Examples
```
demisto-sdk spell-check -p Integrations/HelloWorld/HelloWorld_description.md
```
This will check the spelling of words in the file "HelloWorld_description.md".
<br/><br/>
```
demisto-sdk spell-check -p Integrations/HelloWorld/HelloWorld.yml --known-words MyDictionaryFile.txt
```
This will check the spelling of words in the file "HelloWorld.yml" and will treat wll words in "MyDictionaryFile.txt".
<br/><br/>
```
demisto-sdk spell-check -p Playbooks/playbook-myPlaybook.yml
```
This will check the spelling of words in the file "playbook-myPlaybook.yml".
