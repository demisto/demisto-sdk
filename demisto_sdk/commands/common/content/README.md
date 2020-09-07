# DemistoContentPython Libary

[Contribution guide](docs/CONTRIBUTION.md)

# Overview
The DemistoContentPython Libary is located in `<demisto-sdk repository>/demisto_sdk/commands/common/content`

ContentPython is a python library used to interact with the Demisto Content repository with high-level abstraction.

It provides abstractions of Demisto-Content objects for easy access of repository data and additionally allows you to access the Pickled file objects (Yaml, Json) more directly using a pure python implementation.

# Import

Import DemistoContentPython Library:

```python
import demisto_sdk.commands.common.content as content_py
```

Import DemistoContentPython Library Objects:
```python
from demisto_sdk.commands.common.content import (Content, ContentError,
                                                 ContentFactoryError, Pack)
```

# Getting Started

1. Accessing the `Content` object:

```python
from demisto_sdk.commands.common.content import Content

content: Content = Content.from_cwd()
```

The 'from_cwd' class method will determine the content repository path by traversing the parent's directories in the current working directory.

> If this method is executed not in Content Repository, the Current Working Directory will be configured as Content root directory.
> If it is not a valid Content folder structure no exception will be raised -> Child object will not be found (Packs, Documentations, etc.)

2. Accessing Content `Root` objects:

```python
from demisto_sdk.commands.common.content import Content, Documentation

content: Content = Content.from_cwd()

for documentation in content.documentations:
    isinstance(documentation, Documentation)  # True
```

3. Accessing `Pack` objects:

    a. Iterating over all packs -

    ```python
    from demisto_sdk.commands.common.content import Content, Pack

    content: Content = Content.from_cwd()

    for pack_id, pack_obj in content.packs:
        isinstance(pack_obj, Pack)  # True
    ```

    b. Access pack by name -

    ```python
    from demisto_sdk.commands.common.content import Content, Pack

    content = Content.from_cwd()

    pack: Pack = content.packs['Akamai_WAF']
    isinstance(pack, Pack)  # True
    ```

   c. Access pack internal objects -

   ```python
   from demisto_sdk.commands.common.content import (Content, Pack, Integration, Script,
                                                   Playbook, IncidentType, AgentTool,
                                                   PackIgnore, SecretIgnore)

   content: Content = Content.from_cwd()

   pack_obj: Pack
   for pack_id, pack_obj in content.packs:
       # Access Integration objects
       for integration in pack_obj.integrations:
           isinstance(integration, Integration)  # True
       # Access script objects
       for script in pack_obj.scripts:
          isinstance(script, Script)  # True
       # Access playbook objects
       for playbook in pack_obj.playbooks:
          isinstance(playbook, Playbook)  # True
       # Access incident type objects
       for incident_type in pack_obj.incident_types:
          isinstance(incident_type, IncidentType)  # True
       # Access tools objects
       for tool in pack_obj.tools:
          isinstance(tool, AgentTool)  # True
       # Access pack-ignore object
       pack_ignore: PackIgnore = pack_obj.pack_ignore
       # Access secrets-ignore object
       secrets_ignore: SecretIgnore = pack_obj.secrets_ignore
   ```

   d. Interact with internal pack-objects -

   ```python
   from demisto_sdk.commands.common.content import Content, Pack, Integration, IncidentType

   content: Content = Content.from_cwd()

   pack: Pack = content.packs['Akamai_WAF']
   integration: Integration
   for integration in pack.integrations:
      integration.to_dict() # Yaml to dict.
      integration_path = integration.path # Integration yaml path.
      code_path = integration.code_path # Integration py/ps1/js code path if not unified else None.
      description_path = integration.description_path # Integration description path if not unified else None.
      img_path = integration.png_path # Integration image path if not unified else None.
      changelog_path = integration.changelog # Integration Changelog object if not defined None.
      readme_path = integration.changelog # Integration Readme object if not defined None.
      from_version = integration.from_version # from_version attribute in Yaml/JSON
      docker_image = integration.docker_image # docker_image attribute in Yaml/JSON

   incident_type: IncidentType
   for incident_type in pack.incident_types:
      incident_type.to_dict() # JSON to dict.
      incident_type_path = incident_type.path # Incident type json path.
      changelog_path = incident_type.changelog # Incident type Changelog object if not defined None.
      readme_path = incident_type.changelog # Incident type Readme object if not defined None.
      from_version = incident_type.from_version # from_version attribute in JSON
   ```
