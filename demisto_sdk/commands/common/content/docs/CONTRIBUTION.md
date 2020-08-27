# Contribution guide

## Getting started

1. [Content objects overview.](#1-content-objects-overview)
2. [Adding a new Content Root object (Documentation / id_set.json, etc.).](#2-adding-a-new-content-root-object-documentations-id_setjson-etc)
3. [Adding a new Content Pack object (Integration/Script/IncidentType etc).](#3-adding-a-new-content-pack-object-integration-script-incidenttype-etc)
4. [Enhance existing Internal Pack object (Integration/Script/IncidentType etc).](#4-enhance-an-existing-internal-pack-object-integration-script-incidenttype-etc)


## 1. Content objects overview
Every Content object (excluding Pack, Content) based on:
 - `TextObject` - Object based on any Text file (for example Readme).
 - `JSONObject` - Object based on any JSON file (for example Readme).
 - `YAMLObject` - Object based on any YAML file (for example Readme).
 - `JSONObject` -> `JSONContentObject` - Object based on any valid JSON file (for example Widget).
 - `YAMLObject` -> `YAMLContentObject` - Object based on any valid YAML file (for example Playbook).
 - `YAMLContentObject` -> `YAMLContentUnfiedObject` - Object based on any valid YAML file which is also unify-able (for example Integration).

 > "**->**" This sign means inheritance


## 2. Adding a new Content Root object (Documentations/ id_set.json etc)
Content root objects are located in : `demisto_sdk/commands/common/content/objects/root_objects`

New objects should be in the following structure: `demisto_sdk/commands/common/content/objects/root_objects/<new-obj>`

The structure should contain a single file `<new-object>.py` (snake-case) with the following content:
```python
from typing import Union

from demisto_sdk.commands.common.content.objects.abstract_objects.json_object import JSONObject
from wcmatch.pathlib import Path


class NewObject(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
```

## 3. Adding a new Content Pack object (Integration, Script, IncidentType, etc.)
Content pack objects are located in : `demisto_sdk/commands/common/content/objects/pack_objects`

New objects should be in the following path: `demisto_sdk/commands/common/content/objects/pack_objects/<new-obj>`

The folder should contain a single file `<new-object>.py` (snake-case) with the following content:
```python
from typing import Union

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path


class NewObject(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, 'file-prefix')
```

## 4. Enhance an existing Internal Pack object (Integration, Script, IncidentType, etc.)
All pack objects can be found in `demisto_sdk/commands/common/content/objects/pack_objects/<object>`


Existing code:
```python
from typing import Union

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path


class NewObject(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, 'file-prefix')
```

Adding property example:
```python
from typing import Union

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path


class NewObject(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, 'file-prefix')

    @property
    def new_property(self):
        return self.get('id') # Some valid property in YAML file.
```
