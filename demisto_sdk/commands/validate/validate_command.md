## Validate

Makes sure your content repository files are in order and have valid yml file scheme.

**Use Cases**
This command is used to make sure that the content repo files are valid and are able to be processed by Demisto.
This is used in our validation process both locally and in Circle CI.

**Arguments**:
* **--no-backward-comp**
Whether to check backward compatibility or not.
* **-j, --conf-json**
Validate the conf.json file.
* **-i, --id-set**
Create the id_set.json file.
* **--prev-ver**
Previous branch or SHA1 commit to run checks against.
* **-g, --use-git**
Validate changes using git - this will check your branch changes and will run only on them.
* **--post-commit**
Whether the validation is done after you committed your files, this will help the command to determine which files it
 should check in its run. Before you commit the files it should not be used. Mostly for build validations.
* **-p, --path**
Path of file to validate specifically.

**Examples**:
`demisto-sdk validate`
This will validate all the files in content repo.
<br><br>

`demisto-sdk validate -g --no-backwards-comp`
This will validate only changed files from content origin/master branch and will exclude backwards
compatibility checks.
<br><br>

`demisto-sdk validate -i -j`
This will validate all content repo files and including conf.json file and will create the id_set.json file.
<br><br>

`demisto-sdk validate --prev-ver SHA1-HASH`
This will validate only changed files from the branch given (SHA1).
<br><br>

`demisto-sdk validate --post-commit`
This indicates that the command runs post commit.
<br><br>

`demisto-sdk validate -p Integrations/Pwned-V2/Pwned-V2.yml`
This will validate the file Integrations/Pwned-V2/Pwned-V2.yml only.
<br><br>
