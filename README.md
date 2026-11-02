# PubMed Related Paper

A `nanoagent.plugin/v0001` plugin, created by `nanoagent plugin new` with the
structure of NanoAgent's reference plugin,
[arxiv-source](https://github.com/zeyuyang8/arxiv-source).

Given a PMID, it returns the other PubMed article with the highest ELink
neighbor score.

## Tools

| Tool | Does | Code |
|---|---|---|
| `most_related_paper` | Loads PubMed neighbor scores for a PMID and returns the highest-scoring other article | `src/plugin/most_related.py` |
| `pin_related_paper` | Computes the same article as the task's answer key, and writes no file | `src/plugin/pin.py` |

`most_related_paper` writes `neighbors.json` in the workspace: the query PMID and one row per other neighbor, with the ELink `score` stored as `neighbor_score`. The query PMID is dropped when NCBI includes it. Equal scores select the numerically smaller PMID. A neighbor list that contains only the query PMID raises instead of returning that paper.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `pubmed-related-paper` | Returns the most related PMID | `tool`, with `most_related_paper` and reference `pin_related_paper` |

The input is `pmid`. The output is `related_pmid` and `neighbor_score`.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs, never values
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, and the plugin's own modules
├── tests/
├── ui/              # how the page draws the outputs: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

`contract.py` is the one place a value's shape is declared. Its `Output`
classes are the JSON Schemas the server offers and the agent sees, and every
input and output is built into its class on the way in and out: the server,
NanoAgent and the verifier all get typed values, never loose dicts. A tool
that fails raises; NanoAgent sees an MCP error.

## Develop and run

```bash
uv sync --extra dev
uv run pytest
```

The tests use a fake HTTP client and do not call NCBI. A live run needs
network access to `eutils.ncbi.nlm.nih.gov`. `NCBI_API_KEY` and `NCBI_EMAIL`
are listed in `.env`. The client sends them on the E-utilities request when
they are non-empty, and still ranks when they are empty. No workspace file is
required before a run; `most_related_paper` creates `neighbors.json`.
