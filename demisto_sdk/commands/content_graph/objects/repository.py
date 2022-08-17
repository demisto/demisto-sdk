import multiprocessing
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Any, Dict, Iterator, List, Tuple
from demisto_sdk.commands.content_graph.objects.pack import Pack

from demisto_sdk.commands.content_graph.constants import ContentTypes, NodeData, Rel, RelationshipData, PACKS_FOLDER



class Repository(BaseModel):
    path: Path
    packs: List[Pack]
        

