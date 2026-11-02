"""The task tool: record the neighbor scores and return the most related other article."""

from __future__ import annotations

import json
from pathlib import Path

from contract import RelatedInput, RelatedOutput
from plugin.client import get_client
from plugin.related import find_related

NEIGHBORS_FILE = "neighbors.json"


def most_related_paper(given: RelatedInput, workspace: Path) -> RelatedOutput:
    output, neighbors = find_related(given, get_client())
    payload = {"pmid": given.pmid, "neighbors": neighbors}
    (workspace / NEIGHBORS_FILE).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output
