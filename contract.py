"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    MOST_RELATED = "most_related_paper"
    PIN_RELATED = "pin_related_paper"


class Task(Enum):
    PUBMED_RELATED_PAPER = "pubmed-related-paper"


@dataclass
class RelatedInput(Output):
    pmid: Annotated[str, "PubMed ID of the paper whose most related neighbor to find"]


@dataclass
class RelatedOutput(Output):
    related_pmid: Annotated[str, "PubMed ID of the other article with the highest neighbor score"]
    neighbor_score: Annotated[int, "ELink score of that article; the query PMID is excluded"]


TOOLS = {
    Tool.MOST_RELATED: (RelatedInput, RelatedOutput),
    Tool.PIN_RELATED: (RelatedInput, RelatedOutput),
}
TASKS = {Task.PUBMED_RELATED_PAPER: (RelatedInput, RelatedOutput)}
