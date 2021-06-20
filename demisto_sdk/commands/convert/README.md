## convert

**Convert layouts and classifiers from a new version to an old version and vice versa.**

##Note:
**Classifiers/Mappers conversion from 6.0.0 and above to versions 5.9.9 and below is currently not supported. Request for converting a pack for versions below 6.0.0 will result on layouts conversion only.**

### Conversions
| Entity Type | From Version | To Version | Supported
| --- | --- | --- | --- |
| Layout | 5.5.0 | 6.0.0 | Yes |
| Layout | 6.0.0 | 5.5.0 | Yes |
| Classifier | 5.5.0 | 6.0.0 | Yes |
| Classifier | 6.0.0 | 5.5.0 | No |

### Use Cases
This command is used to convert entities such as Layouts/Classifiers between XSOAR versions.


### Arguments
* **-i PACK_PATH/ENTITY_DIR_PATH, --input PACK_PATH/ENTITY_DIR_PATH**

    The path of a package directory, or entity directory (Layouts, Classifiers) that contains the entities to be converted.

* **-v, --version**

    Version to convert the entities in the given input to.

### Examples
```
demisto-sdk convert -i Packs/TestPack1 -v 6.0.0
```
This will convert all layouts and classifiers in "TestPack1" pack to 6.0.0 file structure.
```
demisto-sdk convert -i Packs/TestPack1/Layouts -v 5.5.0
```
This will convert all new layouts in TestPack1 pack to the layout 5.9.9 and below files structure.
```
demisto-sdk convert -i Packs/TestPack1/Classifiers -v 6.0.0
```
This will convert all classifiers in "TestPack1" pack to 6.0.0 file structure.
```
demisto-sdk convert -i Packs/TestPack1/Classifiers -v 5.5.0
```
This will not convert classifiers from 6.0.0 to 5.9.9 and below because it is currently not supported
