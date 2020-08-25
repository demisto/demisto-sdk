# Contribution guide

## Getting started

1. [Content objects overview.](#1-content-objects)
2. [Adding new Content Root object (Documentations/ id_set.json etc)](#2-adding-new-content-root-object-documentations-id_setjson-etc)
3. [Adding new Content Pack object (Integration/Script/IncidentType etc).](#3-adding-new-content-pack-object-integrationscriptincidenttype-etc)
4. [Enhance existing Intenal Pack object (Integration/Script/IncidentType etc)](#4-enhance-existing-intenal-pack-object-integrationscriptincidenttype-etc)


## 1. Content objects overview
Every Content object (excluding Pack, Content) based on:
 - `TextObject` - Object based on any Text file (for example Readme).
 - `JSONObject` - Object based on any JSON file (for example Readme).
 - `YAMLObject` - Object based on any YAML file (for example Readme).
 - `JSONObject` -> `JSONContentObject` - Object based on any valid JSON file (for example Widget).
 - `YAMLObject` -> `YAMLContentObject` - Object based on any valid YAML file (for example Playbook).
 - `YAMLContentObject` -> `YAMLContentUnfiedObject` - Object based on any valid YAML file which is also unify-able (for example Integration).

 > **->** - This sign means inheritace


## 2. Adding new Content Root object (Documentations/ id_set.json etc)
Content root objects located in : `demisto_sdk/commands/common/content/objects/root_objects`

New object should be in the following structure: `demisto_sdk/commands/common/content/objects/root_objects/<new-obj>`

Which contain single file `<object-name>.py` (snake-case) with the foloowing content:
```python
from typing import Union

from demisto_sdk.commands.common.content.objects.abstract_objects.json_object import JSONObject
from wcmatch.pathlib import Path


class NewObject(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
```

## 3. Adding new Content Pack object (Integration/Script/IncidentType etc)
Content pack objects located in : `demisto_sdk/commands/common/content/objects/pack_objects`

New object should be in the following path: `demisto_sdk/commands/common/content/objects/pack_objects/<new-obj>`

Which contain single file `<object-name>.py` (snake-case) with the foloowing content:
```python
from typing import Union

from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path


class NewObject(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, 'file-prefix')
```

## 4. Enhance existing Intenal Pack object (Integration/Script/IncidentType etc)
All packs object can be found in `demisto_sdk/commands/common/content/objects/pack_objects/<object>`


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
