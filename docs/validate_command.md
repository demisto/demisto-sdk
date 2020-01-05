### Validate

Makes sure your content repository files are in order and have valid yml file scheme.

**Use Cases**
This command is used to make sure that the content repo files are valid and are able to be processed by Demisto.
This is used in our validation process both locally and in Circle CI.

**Arguments**:
* **-c CIRCLE, --circle CIRCLE**
                        Does this command run in CircleCi or not.
* **-b BACKWARD_COMP, --backward-comp BACKWARD_COMP**
                        Whether to check backward compatibility or not.
* **-j, --conf-json**
                        Validate the conf.json file.
* **-i, --id-set**
                        Create the id_set.json file.
* **-p PREV_VER, --prev-ver PREV_VER**
                        Previous branch or SHA1 commit to run checks against.
* **-g, --use-git**
                        Validate only changed files from content repo's origin/master branch.

**Examples**:
`demisto-sdk validate`
This will validate all the files in content repo.

`demisto-sdk validate -g -b`
This will validate only changed files from content origin/master branch and will also check them for backwards
compatibility issues.

`demisto-sdk validate -i -j`
This will validate all content repo files and including conf.json file and will create the id_set.json file.

`demisto-sdk validate -c -p SHA1-HASH`
This indicates validate runs on Circle CI and will validate only changed files from the branch given (SHA1).
