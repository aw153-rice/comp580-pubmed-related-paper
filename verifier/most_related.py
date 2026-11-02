"""Checks for most_related_paper and the pubmed-related-paper task."""

from .checks import result
from .identity import input_problem, output_problem
from .rows import load_neighbors, matches_rows


def verify_input(value):
    problem = input_problem(value)
    if problem:
        return result(False, problem[1])
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    problem = input_problem(input_value) or output_problem(output_value, input_value.pmid)
    if problem:
        return result(False, problem[1])
    kind, payload = load_neighbors(workspace, input_value.pmid)
    if kind != "ok":
        return result(False, payload)
    if not matches_rows(output_value, payload):
        return result(False, "output is not the most related paper in neighbors.json")
    return result(True, "output matches the ranked neighbors")


def verify_task(arguments, output, reference, workspace):
    problem = input_problem(arguments) or output_problem(output, arguments.pmid)
    if problem:
        return result(False, problem[1])
    if reference is None:
        return result(False, "reference is missing")
    problem = output_problem(reference, arguments.pmid)
    if problem:
        return result(False, problem[1])
    if output.related_pmid != reference.related_pmid or output.neighbor_score != reference.neighbor_score:
        return result(False, "output does not match the reference")
    kind, payload = load_neighbors(workspace, arguments.pmid)
    if kind != "ok":
        return result(False, payload)
    if not matches_rows(output, payload):
        return result(False, "neighbors.json does not support the output")
    return result(True, "output matches the reference")
