"""Read neighbors.json and recompute the winner. The stored order is not trusted."""

import json
from pathlib import Path

from .identity import PMID
from .rank import choose_top


def load_neighbors(workspace, query_pmid):
    """Return ("ok", neighbors), or ("missing"|"malformed", message)."""
    path = Path(workspace) / "neighbors.json"
    if not path.is_file():
        return ("missing", "neighbors.json is missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ("malformed", "neighbors.json is not JSON")
    if type(data) is not dict or type(data.get("neighbors")) is not list:
        return ("malformed", "neighbors.json has no neighbors list")
    if data.get("pmid") != query_pmid:
        return ("malformed", "neighbors.json is for a different pmid")
    neighbors = []
    seen = []
    for row in data["neighbors"]:
        if type(row) is not dict:
            return ("malformed", "neighbors.json has a neighbor that is not an object")
        pmid = row.get("pmid")
        score = row.get("neighbor_score")
        if type(pmid) is not str or PMID.fullmatch(pmid) is None:
            return ("malformed", "neighbors.json has an invalid pmid")
        if pmid == query_pmid:
            return ("malformed", "neighbors.json includes the query pmid")
        if type(score) is not int or score < 0:
            return ("malformed", "neighbors.json has an invalid neighbor_score")
        if pmid in seen:
            return ("malformed", "neighbors.json repeats a pmid")
        seen.append(pmid)
        neighbors.append({"pmid": pmid, "neighbor_score": score})
    if not neighbors:
        return ("malformed", "neighbors.json lists no neighbors")
    return ("ok", neighbors)


def matches_rows(output, neighbors):
    winner = choose_top(neighbors)
    return output.related_pmid == winner["pmid"] and output.neighbor_score == winner["neighbor_score"]
