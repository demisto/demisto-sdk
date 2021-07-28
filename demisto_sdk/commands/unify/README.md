## Unify

This command has two main functions:

1. #### YML Unifier:

    Unifies integration/script code, image, description and yml files to a single XSOAR yml file.

    **Use Cases**:
    This command is used in order to create a unified yml file, able to be uploaded to Demisto via the
    "Upload Integration" or "Upload Script" buttons, in Demisto's Settings and Automation tabs respectively.

    **Arguments**:
    * **-i, --input**
      The path to the directory of an integration/script in which the files reside
    * **-o, --output**
      The path to the directory into which to write the unified yml file
    * **--force**
      Forcefully overwrites the preexisting yml if one exists

    **Examples**:
    `demisto-sdk unify -i Integrations/MyInt -o Integrations`
    This will grab the integration components in "Integrations/MyInt" directory and unify them to a single yaml file
    that will be created in the "Integrations" directory.
    <br/><br/>

    `demisto-sdk unify -i Scripts/MyScr -o Scripts`
    This will grab the script components in "Scripts/MyScr" directory and unify them to a single yaml file
    that will be created in the "Scripts" directory.

 2. #### GenericModule Unifier:

    Unifies a GenericModule with its Dashboards to a single JSON object.

    **Use Cases**:
    This command is used in order to create a unified GenericModule file, able to be uploaded to Demisto.

    **Arguments**:
    * **-i, --input**
      The path to a GenericModule *file* to unify
    * **-o, --output**
      The path to the directory into which to write the unified GenericModule file
    * **--force**
      Forcefully overwrites the preexisting unified GenericModule file if one exists

    **Examples**:
    `demisto-sdk unify -i Packs/RBVM/GenericModules/genericmodule-RBVM.json`
    This will grab the GenericModule input file "genericmodule-RBVM.json", unify it with its dashboards and save
    the unified file in the same directory as the input file ("Packs/RBVM/GenericModules").
    <br/><br/>

    `demisto-sdk unify -i Packs/RBVM/GenericModules/genericmodule-RBVM.json -o Packs/RBVM/`
    This will grab the GenericModule input file "genericmodule-RBVM.json", unify it with its dashboards and save
    the unified file in the given output directory ("Packs/RBVM/").
