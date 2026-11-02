"""PMID checks for the query and the chosen neighbor."""

import re

PMID = re.compile(r"^[1-9][0-9]{0,8}$")


def input_problem(value):
    """A (kind, message) pair, or None when the PMID can be looked up."""
    if value.pmid.strip() == "":
        return ("missing", "pmid is empty")
    if PMID.fullmatch(value.pmid) is None:
        return ("malformed", "pmid is not a PubMed id")
    return None


def output_problem(output, query_pmid):
    """A (kind, message) pair, or None when the two fields can name another paper."""
    if output.related_pmid.strip() == "":
        return ("missing", "related_pmid is empty")
    if PMID.fullmatch(output.related_pmid) is None:
        return ("malformed", "related_pmid is not a PubMed id")
    if type(output.neighbor_score) is not int or output.neighbor_score < 0:
        return ("malformed", "neighbor_score must be zero or greater")
    if output.related_pmid == query_pmid:
        return ("wrong", "related_pmid is the query pmid")
    return None
