# flake8: noqa
from __future__ import absolute_import

import inspect

from .content import *  # lgtm [py/polluting-import]
from .errors import *  # lgtm [py/polluting-import]
from .objects.pack_objects import *  # lgtm [py/polluting-import]
from .objects.root_objects import *  # lgtm [py/polluting-import]
from .objects_factory import *  # lgtm [py/polluting-import]

# Define content packs all types object
PackObject = Union[Classifier, OldClassifier, ClassifierMapper, Connection, Dashboard, DocFile, IncidentField,
                   IncidentType, IncidentField, IndicatorType, OldIndicatorType, Integration, Layout, PackIgnore,
                   PackMetaData, Playbook, Readme, ReleaseNote, Report, Script, SecretIgnore, AgentTool, Widget]


# Define content packs all types object
RootObject = Union[ContentDescriptor, Documentation]

__all__ = [name for name, obj in locals().items()
           if not (name.startswith('_') or inspect.ismodule(obj))]
