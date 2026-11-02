"""Tool tests. The HTTP client is a fake, so nothing here opens a socket."""

import json
from pathlib import Path

import httpx
import pytest
from slimconfig import build_output

from contract import RelatedInput
from plugin.client import ELINK_URL, HttpxClient, set_client
from plugin.most_related import most_related_paper
from plugin.pin import pin_related_paper

QUERY = {"pmid": "100"}


class FakeClient:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def get_json(self, url, params):
        self.calls.append((url, dict(params)))
        return self.handler(url, params)


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.delenv("NCBI_EMAIL", raising=False)
    holder = {}

    def install(handler):
        client = FakeClient(handler)
        holder["client"] = client
        set_client(client)
        return client

    yield install
    set_client(None)


def given(**overrides):
    return build_output({**QUERY, **overrides}, RelatedInput)


def elink(links, pmid="100", linkname="pubmed_pubmed"):
    return {
        "linksets": [
            {
                "dbfrom": "pubmed",
                "ids": [pmid],
                "linksetdbs": [{"dbto": "pubmed", "linkname": linkname, "links": links}],
            }
        ]
    }


def scripted(body):
    def handler(url, params):
        if isinstance(body, Exception):
            raise body
        return body

    return handler


def test_ranks_the_highest_score_and_drops_the_query(fake, tmp_path: Path):
    links = [
        {"id": "100", "score": 999},
        {"id": "400", "score": 10},
        {"id": "200", "score": 50},
        {"id": "300", "score": 50},
    ]
    client = fake(scripted(elink(links)))
    output = most_related_paper(given(), tmp_path)
    assert (output.related_pmid, output.neighbor_score) == ("200", 50)
    saved = json.loads((tmp_path / "neighbors.json").read_text(encoding="utf-8"))
    assert saved["pmid"] == "100"
    assert saved["neighbors"] == [
        {"pmid": "400", "neighbor_score": 10},
        {"pmid": "200", "neighbor_score": 50},
        {"pmid": "300", "neighbor_score": 50},
    ]
    sent = client.calls[0][1]
    assert client.calls[0][0] == ELINK_URL
    assert sent["cmd"] == "neighbor_score"
    assert sent["linkname"] == "pubmed_pubmed"
    assert sent["db"] == "pubmed"
    assert sent["dbfrom"] == "pubmed"
    assert sent["id"] == "100"
    assert sent["retmode"] == "json"
    assert sent["tool"] == "pubmed-related-paper"
    assert "email" not in sent
    assert "api_key" not in sent


def test_tie_selects_the_lower_pmid_when_the_query_is_absent(fake, tmp_path: Path):
    links = [{"id": "300", "score": 50}, {"id": "200", "score": 50}]
    fake(scripted(elink(links)))
    output = most_related_paper(given(), tmp_path)
    assert (output.related_pmid, output.neighbor_score) == ("200", 50)


def test_a_single_neighbor_with_score_zero_wins(fake, tmp_path: Path):
    fake(scripted(elink([{"id": "9", "score": 0}], pmid="1")))
    output = most_related_paper(given(pmid="1"), tmp_path)
    assert (output.related_pmid, output.neighbor_score) == ("9", 0)


def test_a_nine_digit_pmid_is_accepted(fake, tmp_path: Path):
    pmid = "123456789"
    fake(scripted(elink([{"id": "123456788", "score": 1}], pmid=pmid)))
    output = most_related_paper(given(pmid=pmid), tmp_path)
    assert output.related_pmid == "123456788"


def test_integer_neighbor_ids_are_accepted(fake, tmp_path: Path):
    fake(scripted(elink([{"id": 200, "score": 4}, {"id": 300, "score": 9}])))
    output = most_related_paper(given(), tmp_path)
    assert (output.related_pmid, output.neighbor_score) == ("300", 9)


def test_pin_does_not_write_a_file(fake, tmp_path: Path):
    fake(scripted(elink([{"id": "200", "score": 4}])))
    output = pin_related_paper(given(), tmp_path)
    assert output.related_pmid == "200"
    assert list(tmp_path.iterdir()) == []


def test_sends_optional_credentials(fake, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("NCBI_EMAIL", "reader@example.com")
    monkeypatch.setenv("NCBI_API_KEY", "secret")
    client = fake(scripted(elink([{"id": "200", "score": 1}])))
    most_related_paper(given(), tmp_path)
    sent = client.calls[0][1]
    assert sent["email"] == "reader@example.com"
    assert sent["api_key"] == "secret"


@pytest.mark.parametrize(
    ("pmid", "match"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("0100", "PubMed id"),
        ("100a", "PubMed id"),
        ("1" * 10, "PubMed id"),
    ],
)
def test_rejects_a_bad_pmid(fake, tmp_path: Path, pmid, match):
    fake(scripted(elink([])))
    with pytest.raises(ValueError, match=match):
        most_related_paper(given(pmid=pmid), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_raises_when_the_only_neighbor_is_the_query(fake, tmp_path: Path):
    fake(scripted(elink([{"id": "100", "score": 999}])))
    with pytest.raises(RuntimeError, match="no related paper"):
        most_related_paper(given(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_raises_when_linksetdbs_are_absent(fake, tmp_path: Path):
    body = {"linksets": [{"ids": ["100"]}]}
    fake(scripted(body))
    with pytest.raises(RuntimeError, match="no related paper"):
        most_related_paper(given(), tmp_path)


def test_raises_when_the_link_list_is_empty(fake, tmp_path: Path):
    fake(scripted(elink([])))
    with pytest.raises(RuntimeError, match="no related paper"):
        most_related_paper(given(), tmp_path)


def test_raises_on_an_elink_error(fake, tmp_path: Path):
    fake(scripted({"error": "down"}))
    with pytest.raises(RuntimeError, match="down"):
        most_related_paper(given(), tmp_path)


def test_raises_on_a_linkset_error(fake, tmp_path: Path):
    fake(scripted({"linksets": [{"ERROR": "missing record", "ids": ["100"]}]}))
    with pytest.raises(RuntimeError, match="missing record"):
        most_related_paper(given(), tmp_path)


def test_raises_when_the_linkset_is_for_another_pmid(fake, tmp_path: Path):
    fake(scripted(elink([{"id": "200", "score": 1}], pmid="999")))
    with pytest.raises(RuntimeError, match="different pmid"):
        most_related_paper(given(), tmp_path)


def test_raises_when_pubmed_pubmed_is_missing(fake, tmp_path: Path):
    fake(scripted(elink([{"id": "200", "score": 1}], linkname="pubmed_pubmed_refs")))
    with pytest.raises(RuntimeError, match="no pubmed_pubmed"):
        most_related_paper(given(), tmp_path)


def test_raises_on_two_pubmed_pubmed_sets(fake, tmp_path: Path):
    body = elink([{"id": "200", "score": 1}])
    extra = {"linkname": "pubmed_pubmed", "links": [{"id": "300", "score": 2}]}
    body["linksets"][0]["linksetdbs"].append(extra)
    fake(scripted(body))
    with pytest.raises(RuntimeError, match="more than one"):
        most_related_paper(given(), tmp_path)


def test_raises_on_a_repeated_neighbor(fake, tmp_path: Path):
    fake(scripted(elink([{"id": "200", "score": 1}, {"id": "200", "score": 2}])))
    with pytest.raises(RuntimeError, match="repeated pmid 200"):
        most_related_paper(given(), tmp_path)


def test_raises_when_the_response_has_the_wrong_shape(fake, tmp_path: Path):
    fake(scripted({"linksets": "nope"}))
    with pytest.raises(TypeError, match="no linksets"):
        most_related_paper(given(), tmp_path)


@pytest.mark.parametrize(
    ("link", "match"),
    [
        ({"id": "0200", "score": 1}, "invalid pmid"),
        ({"id": "200a", "score": 1}, "invalid pmid"),
        ({"id": None, "score": 1}, "invalid pmid"),
        ({"id": "200", "score": -1}, "neighbor_score"),
        ({"id": "200", "score": True}, "neighbor_score"),
        ({"id": "200", "score": 1.5}, "neighbor_score"),
        ({"id": "200", "score": "5"}, "neighbor_score"),
        ({"id": "200"}, "neighbor_score"),
        ("200", "not an object"),
    ],
)
def test_raises_on_a_bad_link(fake, tmp_path: Path, link, match):
    fake(scripted(elink([link])))
    with pytest.raises(TypeError, match=match):
        most_related_paper(given(), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_http_status_non_json_and_non_object_raise():
    def status(_request):
        return httpx.Response(503, text="no")

    client = HttpxClient(transport=httpx.MockTransport(status), pause=0)
    with pytest.raises(RuntimeError, match="HTTP 503"):
        client.get_json(ELINK_URL, {})

    def text(_request):
        return httpx.Response(200, text="not-json")

    client = HttpxClient(transport=httpx.MockTransport(text), pause=0)
    with pytest.raises(RuntimeError, match="not JSON"):
        client.get_json(ELINK_URL, {})

    def listed(_request):
        return httpx.Response(200, json=["not", "an", "object"])

    client = HttpxClient(transport=httpx.MockTransport(listed), pause=0)
    with pytest.raises(TypeError, match="not a JSON object"):
        client.get_json(ELINK_URL, {})
