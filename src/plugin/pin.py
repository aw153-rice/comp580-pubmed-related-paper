"""Reference tool: the same neighbor, with no workspace file, pinned before the task runs."""

from __future__ import annotations

from pathlib import Path

from contract import RelatedInput, RelatedOutput
from plugin.client import get_client
from plugin.related import find_related


def pin_related_paper(given: RelatedInput, _workspace: Path) -> RelatedOutput:
    output, _neighbors = find_related(given, get_client())
    return output
