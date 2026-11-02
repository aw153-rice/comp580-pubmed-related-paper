"""Pick the most related neighbor. src/plugin/rank.py implements this same rule."""


def choose_top(neighbors):
    """Return the neighbor with the highest neighbor_score; equal scores select the smaller PMID."""
    if not neighbors:
        raise ValueError("no neighbors to rank")
    winner = neighbors[0]
    for neighbor in neighbors[1:]:
        higher = neighbor["neighbor_score"] > winner["neighbor_score"]
        tied = neighbor["neighbor_score"] == winner["neighbor_score"] and int(neighbor["pmid"]) < int(winner["pmid"])
        if higher or tied:
            winner = neighbor
    return {"pmid": winner["pmid"], "neighbor_score": winner["neighbor_score"]}
