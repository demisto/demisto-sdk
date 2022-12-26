## Prepare Content

This command will prepare the content to upload to the platform.

If the content item is a a pack, it will create the pack zip.
If the content item is an integration/script/rule, it will create the unified yml file.

**Arguments**
* **-i, --input**
  The path to the directory of a pack or a content item in which the files reside
* **-o, --output**
  The path to the directory into which to write result.
* **-f, --force**
  Forcefully overwrites the file if it exists.
* **-c, --custom**
  Adds a custom label to the name/display/id of the unified yml (only for integrations/scripts).



## Unify

This command has three main functions:

1. #### Integration/Script Unifier:

    Unifies integration/script code, image, description and yml files to a single XSOAR yml file.

    **Use Cases**:
    This command is used in order to create a unified yml file, able to be uploaded to Demisto via the
    "Upload Integration" or "Upload Script" buttons, in Demisto's Settings and Automation tabs respectively.

    **Arguments**:
    * **-i, --input**
      The path to the directory of an integration/script in which the files reside
    * **-o, --output**
      The path to the directory into which to write the unified yml file
    * **-f, --force**
      Forcefully overwrites the preexisting yml if one exists
    * **-c, --custom**
      Adds a custom label to the name/display/id of the unified yml
    * **-ini, --ignore-native-image**
       Whether to ignore the addition of the nativeimage key to the yml of a script/integration. Defaults to False.

    **Examples**:
    `demisto-sdk unify -i Integrations/MyInt -o Integrations`
    This will grab the integration components in "Integrations/MyInt" directory and unify them to a single yaml file
    that will be created in the "Integrations" directory.
    <br/><br/>

    `demisto-sdk unify -i Scripts/MyScr -o Scripts`
    This will grab the script components in "Scripts/MyScr" directory and unify them to a single yaml file
    that will be created in the "Scripts" directory.
    <br/><br/>

    `demisto-sdk unify -u Integrations/MyInt -c Test`
    This will append to the unified yml name/script/id a label ' - Test' that will prevent bumps
    with the uploaded unified yml and the original integration/script on the server.
    origin yml: `{name: integration}` --> unified yml: `{name: integration - Test}`

2. #### GenericModule Unifier:

   Unifies a GenericModule with its Dashboards to a single JSON object.

   **Use Cases**:
   This command is used in order to create a unified GenericModule file, able to be uploaded to Demisto.

   **Arguments**:
   * **-i, --input**
     The path to a GenericModule *file* to unify
   * **-o, --output**
     The path to the directory into which to write the unified GenericModule file
   * **-f --force**
     Forcefully overwrites the preexisting unified GenericModule file if one exists

   **Examples**:
   `demisto-sdk unify -i Packs/RBVM/GenericModules/genericmodule-RBVM.json`
   This will take the GenericModule input file "genericmodule-RBVM.json", unify it with its dashboards and save
   the unified file in the same directory as the input file ("Packs/RBVM/GenericModules").
   <br/><br/>

   `demisto-sdk unify -i Packs/RBVM/GenericModules/genericmodule-RBVM.json -o Packs/RBVM/`
   This will take the GenericModule input file "genericmodule-RBVM.json", unify it with its dashboards and save
   the unified file in the given output directory ("Packs/RBVM/").

3. #### Parsing/Modeling Rule Unifier:

    Unifies Parsing/Modeling rule YML, XIF and samples JSON files to a single YML file.

    **Use Cases**:
    This command is used in order to create a unified YML file, able to be uploaded to Cortex XSIAM as part of a Content Pack.

    **Arguments**:
    * **-i, --input**
      The path to the directory of a parsing/modeling rule in which the files reside.
    * **-o, --output**
      The path to the directory into which to write the unified YML file.
    * **--force**
      Forcefully overwrites the preexisting YML if one exists.

    **Examples**:
    `demisto-sdk unify -i Packs/SIEMPack/ParsingRule/MyParsingRule -o Packs/SIEMPack/ParsingRule`
    This will grab the parsing rules components (YAML, XIF and JSON) from the `ParsingRule/MyParsingRule` directory and unify them to a single YAML file that will be created in the "ParsingRules" directory.
