## prepare-content
This command prepares content to upload to the platform. If the content item is a pack, prepare-content creates the pack zip file. If the content item is an integration/script/rule, prepare-content creates the unified YAML file.

NOTE: The prepare-content command replaces the unify command.

**Arguments**
* **-i, --input**
  The path to the directory of a pack or a content item in which the files reside
* **-o, --output**
  The path to the directory into which to write result.
* **-f, --force**
  Forcefully overwrites the file if it exists.
* **-c, --custom**
  Adds a custom label to the name/display/id of the unified yml (only for integrations/scripts).

    **Examples**:
       <br/><br/>
    `​​demisto-sdk prepare-content -i Integrations/MyInt -o Integrations​​`
    Takes the integration components in ​Integrations/MyInt​ directory and unifies them to a single YAML file that is created
    in the ​Integrations​​ directory.
    <br/><br/>

    `demisto-sdk prepare-content -i Scripts/MyScr -o Scripts​​`
    Takes the script components in ​Scripts/MyScr​ directory and unifies them to a single YAML
    file that is created in the ​Scripts​​ directory.
    <br/><br/>

    `demisto-sdk prepare-content -u Integrations/MyInt -c Test​​`
    Appends to the unified YAML name/script/id a label ​- Test​ that prevents bumps
    with the uploaded unified YAML and the original integration/script on the server.
​    origin yml: {name: integration} --> unified yml: {name: integration - Test}
    <br/><br/>

   `demisto-sdk prepare-content -i Packs/RBVM/GenericModules/genericmodule-RBVM.json​​`
   Takes the GenericModule input file ​genericmodule-RBVM.json​​, unifies it with its dashboards
   and saves the unified file in the same directory as the input file ​Packs/RBVM/GenericModules​​.
   <br/><br/>

   `​​demisto-sdk prepare-content -i Packs/RBVM/GenericModules/genericmodule-RBVM.json -o Packs/RBVM/​​`
   Takes the GenericModule input file ​genericmodule-RBVM.json​​, unifies it with its dashboards and
   saves the unified file in the given output directory ​Packs/RBVM​​.
   <br/><br/>

   `demisto-sdk prepare-content -i Packs/SIEMPack/ParsingRule/MyParsingRule -o Packs/SIEMPack/ParsingRule`
    Takes the parsing rules components (YAML, XIF and JSON) from the ​​ParsingRule/MyParsingRule​​ directory
    and unifies them into a single YAML file that is created in the ​ParsingRules​​ directory.
