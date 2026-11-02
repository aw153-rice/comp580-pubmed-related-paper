"""Offline ranking cases shared by the plugin and the verifier."""

import pytest

from plugin.rank import choose_top as plugin_choose
from verifier.rank import choose_top as verifier_choose

TIED = [
    {"pmid": "300", "neighbor_score": 50},
    {"pmid": "200", "neighbor_score": 50},
]
HIGHER = [
    {"pmid": "400", "neighbor_score": 10},
    {"pmid": "200", "neighbor_score": 50},
]
ZERO = [{"pmid": "5", "neighbor_score": 0}]
THREE = [
    {"pmid": "9", "neighbor_score": 3},
    {"pmid": "8", "neighbor_score": 3},
    {"pmid": "7", "neighbor_score": 2},
]


@pytest.mark.parametrize("neighbors", [TIED, HIGHER, ZERO, THREE])
def test_rankers_agree(neighbors):
    assert plugin_choose(neighbors) == verifier_choose(neighbors)


def test_tie_selects_the_lower_pmid():
    assert plugin_choose(TIED) == {"pmid": "200", "neighbor_score": 50}


def test_empty_rows_raise():
    with pytest.raises(ValueError, match="no neighbors"):
        plugin_choose([])
    with pytest.raises(ValueError, match="no neighbors"):
        verifier_choose([])
