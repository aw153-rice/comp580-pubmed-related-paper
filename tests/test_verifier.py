"""Verifier cases: correct, wrong, missing, malformed, and boundary."""

import json
from pathlib import Path

from slimconfig import build_output

import verifier
from contract import RelatedInput, RelatedOutput

QUERY = {"pmid": "100"}
WINNER = {"related_pmid": "200", "neighbor_score": 50}
ROWS = [
    {"pmid": "400", "neighbor_score": 10},
    {"pmid": "200", "neighbor_score": 50},
    {"pmid": "300", "neighbor_score": 50},
]


def given(**overrides):
    return build_output({**QUERY, **overrides}, RelatedInput)


def made(**overrides):
    return build_output({**WINNER, **overrides}, RelatedOutput)


def write_rows(workspace: Path, neighbors, pmid="100") -> None:
    payload = {"pmid": pmid, "neighbors": neighbors}
    (workspace / "neighbors.json").write_text(json.dumps(payload), encoding="utf-8")


def test_verify_input_accepts_a_pmid():
    verdict = verifier.verify_input("most_related_paper", given())
    assert verdict["valid"] is True
    assert verifier.verify_input("pin_related_paper", given())["valid"] is True


def test_verify_input_accepts_short_and_long_pmids():
    assert verifier.verify_input("most_related_paper", given(pmid="1"))["valid"] is True
    assert verifier.verify_input("pin_related_paper", given(pmid="123456789"))["valid"] is True


def test_verify_input_rejects_a_missing_pmid():
    verdict = verifier.verify_input("most_related_paper", given(pmid="   "))
    assert verdict["valid"] is False
    assert "empty" in verdict["message"]


def test_verify_input_rejects_a_malformed_pmid():
    for pmid in ("0100", "100a", "1" * 10):
        verdict = verifier.verify_input("pin_related_paper", given(pmid=pmid))
        assert verdict["valid"] is False
        assert "pmid" in verdict["message"]


def test_verify_output_accepts_the_lower_pmid_on_a_tie(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is True


def test_verify_output_rejects_the_higher_pmid_on_a_tie(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("most_related_paper", given(), made(related_pmid="300"), str(tmp_path))
    assert verdict["valid"] is False
    assert "most related" in verdict["message"]


def test_verify_output_rejects_a_lower_score(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output(
        "most_related_paper",
        given(),
        made(related_pmid="400", neighbor_score=10),
        str(tmp_path),
    )
    assert verdict["valid"] is False
    assert "most related" in verdict["message"]


def test_verify_output_rejects_a_score_that_does_not_match(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("most_related_paper", given(), made(neighbor_score=49), str(tmp_path))
    assert verdict["valid"] is False
    assert "most related" in verdict["message"]


def test_verify_output_rejects_a_missing_file(tmp_path: Path):
    verdict = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "missing" in verdict["message"]


def test_verify_output_rejects_a_malformed_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    for pmid in ("0123", "abc", "1" * 10):
        verdict = verifier.verify_output("most_related_paper", given(), made(related_pmid=pmid), str(tmp_path))
        assert verdict["valid"] is False
        assert "related_pmid" in verdict["message"]


def test_verify_output_rejects_a_negative_score(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("most_related_paper", given(), made(neighbor_score=-1), str(tmp_path))
    assert verdict["valid"] is False
    assert "neighbor_score" in verdict["message"]


def test_verify_output_rejects_an_empty_related_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output("most_related_paper", given(), made(related_pmid=""), str(tmp_path))
    assert verdict["valid"] is False
    assert "empty" in verdict["message"]


def test_verify_output_rejects_the_query_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_output(
        "most_related_paper",
        given(),
        made(related_pmid="100", neighbor_score=999),
        str(tmp_path),
    )
    assert verdict["valid"] is False
    assert "query pmid" in verdict["message"]


def test_verify_output_rejects_a_malformed_file(tmp_path: Path):
    (tmp_path / "neighbors.json").write_text("{", encoding="utf-8")
    verdict = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "JSON" in verdict["message"]


def test_verify_output_rejects_a_file_for_another_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS, pmid="999")
    verdict = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "different pmid" in verdict["message"]


def test_verify_output_rejects_a_file_that_includes_the_query(tmp_path: Path):
    write_rows(tmp_path, [{"pmid": "100", "neighbor_score": 999}, {"pmid": "200", "neighbor_score": 50}])
    verdict = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "query pmid" in verdict["message"]


def test_verify_output_rejects_a_bad_neighbor_in_the_file(tmp_path: Path):
    write_rows(tmp_path, [{"pmid": "0200", "neighbor_score": 50}])
    verdict = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "invalid pmid" in verdict["message"]
    write_rows(tmp_path, [{"pmid": "200", "neighbor_score": -1}])
    negative = verifier.verify_output("most_related_paper", given(), made(), str(tmp_path))
    assert negative["valid"] is False
    assert "neighbor_score" in negative["message"]


def test_verify_output_accepts_a_zero_score(tmp_path: Path):
    papers = [{"pmid": "9", "neighbor_score": 0}]
    write_rows(tmp_path, papers, pmid="1")
    output = made(related_pmid="9", neighbor_score=0)
    verdict = verifier.verify_output("most_related_paper", given(pmid="1"), output, str(tmp_path))
    assert verdict["valid"] is True


def test_pin_output_does_not_need_a_file(tmp_path: Path):
    verdict = verifier.verify_output("pin_related_paper", given(), made(), str(tmp_path))
    assert verdict["valid"] is True


def test_pin_output_rejects_a_malformed_score(tmp_path: Path):
    verdict = verifier.verify_output("pin_related_paper", given(), made(neighbor_score=-1), str(tmp_path))
    assert verdict["valid"] is False
    assert "neighbor_score" in verdict["message"]


def test_verify_task_accepts_an_exact_reference(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    output = made()
    verdict = verifier.verify_task("pubmed-related-paper", given(), output, output, str(tmp_path))
    assert verdict["valid"] is True
    assert verdict["score"] == 1.0


def test_verify_task_rejects_a_different_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("pubmed-related-paper", given(), made(related_pmid="300"), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "reference" in verdict["message"]


def test_verify_task_rejects_a_different_score(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("pubmed-related-paper", given(), made(neighbor_score=10), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "reference" in verdict["message"]


def test_verify_task_accepts_the_workspace_when_the_reference_is_absent(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("pubmed-related-paper", given(), made(), None, str(tmp_path))
    assert verdict["valid"] is True
    absent = verifier.verify_task("pubmed-related-paper", given(), made(), None, str(tmp_path / "empty"))
    assert absent["valid"] is False
    assert "missing" in absent["message"]


def test_verify_task_rejects_a_malformed_pmid(tmp_path: Path):
    write_rows(tmp_path, ROWS)
    verdict = verifier.verify_task("pubmed-related-paper", given(), made(related_pmid="12a"), made(), str(tmp_path))
    assert verdict["valid"] is False
    assert "related_pmid" in verdict["message"]


def test_verify_task_accepts_a_zero_score_boundary(tmp_path: Path):
    papers = [{"pmid": "9", "neighbor_score": 0}]
    write_rows(tmp_path, papers, pmid="1")
    output = made(related_pmid="9", neighbor_score=0)
    arguments = given(pmid="1")
    verdict = verifier.verify_task("pubmed-related-paper", arguments, output, output, str(tmp_path))
    assert verdict["valid"] is True


def test_verify_task_rejects_a_file_that_disagrees_with_the_reference(tmp_path: Path):
    write_rows(tmp_path, [{"pmid": "200", "neighbor_score": 1}, {"pmid": "400", "neighbor_score": 9}])
    output = made()
    verdict = verifier.verify_task("pubmed-related-paper", given(), output, output, str(tmp_path))
    assert verdict["valid"] is False
    assert "neighbors.json" in verdict["message"]
