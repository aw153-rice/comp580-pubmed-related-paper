"""Load PubMed neighbor scores and pick the most related other article."""

from __future__ import annotations

import os
import re

from contract import RelatedInput, RelatedOutput
from plugin.client import ELINK_URL, TOOL_NAME
from plugin.rank import choose_top

PMID = re.compile(r"^[1-9][0-9]{0,8}$")
LINKNAME = "pubmed_pubmed"


def clean_pmid(pmid: str) -> str:
    if pmid.strip() == "":
        raise ValueError("pmid is empty")
    if PMID.fullmatch(pmid) is None:
        raise ValueError(f"pmid is not a PubMed id: {pmid!r}")
    return pmid


def find_related(given: RelatedInput, client) -> tuple[RelatedOutput, list[dict]]:
    pmid = clean_pmid(given.pmid)
    neighbors = neighbor_rows(client, pmid)
    winner = choose_top(neighbors)
    output = RelatedOutput(related_pmid=winner["pmid"], neighbor_score=winner["neighbor_score"])
    return output, neighbors


def neighbor_rows(client, pmid: str) -> list[dict]:
    body = client.get_json(
        ELINK_URL,
        ncbi_params(
            {
                "dbfrom": "pubmed",
                "db": "pubmed",
                "id": pmid,
                "cmd": "neighbor_score",
                "linkname": LINKNAME,
                "retmode": "json",
            }
        ),
    )
    return parse_neighbors(body, pmid)


def parse_neighbors(body: dict, pmid: str) -> list[dict]:
    if body.get("error"):
        raise RuntimeError(f"ELink error: {body['error']}")
    linksets = body.get("linksets")
    if not isinstance(linksets, list):
        raise TypeError("ELink returned no linksets")
    if len(linksets) != 1 or not isinstance(linksets[0], dict):
        raise TypeError("ELink returned no linkset")
    linkset = linksets[0]
    if linkset.get("ERROR") or linkset.get("error"):
        raise RuntimeError(f"ELink error: {linkset.get('ERROR') or linkset.get('error')}")
    ids = linkset.get("ids")
    if not isinstance(ids, list):
        raise TypeError("ELink returned no id list")
    if pmid not in [as_pmid(raw) for raw in ids]:
        raise RuntimeError("ELink linkset is for a different pmid")
    linksetdbs = linkset.get("linksetdbs")
    if linksetdbs is None:
        raise RuntimeError("ELink returned no related paper")
    if not isinstance(linksetdbs, list):
        raise TypeError("ELink returned no linksetdbs")
    matches = [db for db in linksetdbs if isinstance(db, dict) and db.get("linkname") == LINKNAME]
    if not matches:
        raise RuntimeError("ELink returned no pubmed_pubmed links")
    if len(matches) != 1:
        raise RuntimeError("ELink returned more than one pubmed_pubmed link set")
    links = matches[0].get("links")
    if not isinstance(links, list):
        raise TypeError("ELink returned no links")
    neighbors = []
    seen = set()
    for link in links:
        if not isinstance(link, dict):
            raise TypeError("ELink returned a link that is not an object")
        neighbor = as_pmid(link.get("id"))
        if neighbor == pmid:
            continue
        score = as_score(link.get("score"))
        if neighbor in seen:
            raise RuntimeError(f"ELink repeated pmid {neighbor}")
        seen.add(neighbor)
        neighbors.append({"pmid": neighbor, "neighbor_score": score})
    if not neighbors:
        raise RuntimeError("ELink returned no related paper")
    return neighbors


def ncbi_params(extra: dict[str, str]) -> dict[str, str]:
    params = {"tool": TOOL_NAME, **extra}
    email = os.environ.get("NCBI_EMAIL", "").strip()
    api_key = os.environ.get("NCBI_API_KEY", "").strip()
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    return params


def as_pmid(raw) -> str:
    if isinstance(raw, bool) or not isinstance(raw, int | str):
        raise TypeError(f"invalid pmid: {raw!r}")
    text = str(raw).strip()
    if PMID.fullmatch(text) is None:
        raise TypeError(f"invalid pmid: {raw!r}")
    return text


def as_score(raw) -> int:
    if type(raw) is not int or raw < 0:
        raise TypeError(f"invalid neighbor_score: {raw!r}")
    return raw
