# lex-cases — Agent Interface

Semantische Suche über deutsche Bundesgerichtsurteile. Schwester-Tool zu `lex-retriever`.

## Setup

```bash
pip install -e .
python -m lex_cases index BGH   # or index-all for all courts
```

## Public Functions

### `search_case_law(query, courts, laws_cited, date_from, date_to, top_k)`

Semantic search over Leitsätze (headnotes) of German federal court decisions.

```python
from lex_cases import search_case_law

results = search_case_law(
    query="Produzentenhaftung § 823 BGB",
    courts=["BGH"],          # optional: filter by court(s)
    laws_cited=["§ 823 BGB"], # optional: filter by cited law
    date_from="2020-01-01",  # optional: YYYY-MM-DD
    date_to="2024-12-31",    # optional: YYYY-MM-DD
    top_k=10,                # default: 10
)
```

Returns list of dicts:
```python
{
    "court":      "BGH",
    "az":         "IV ZR 123/24",
    "date":       "2024-11-15",
    "type":       "Urteil",          # "Urteil" or "Beschluss"
    "leitsatz":   "Der Schuldner haftet...",
    "laws_cited": ["§ 280 BGB", "§ 823 BGB"],
    "score":      0.91,
    "url":        "https://www.rechtsprechung-im-internet.de/..."
}
```

### `get_case_fulltext(url)`

Fetches Tatbestand + Entscheidungsgründe on-demand from rechtsprechung-im-internet.de.
No local storage — always a live HTTP fetch.

```python
from lex_cases import get_case_fulltext

text = get_case_fulltext("https://www.rechtsprechung-im-internet.de/...")
```

Returns: full decision text as string.

### `get_cases_citing_law(law, paragraph)`

Returns all indexed decisions that cite a specific paragraph.

```python
from lex_cases import get_cases_citing_law

cases = get_cases_citing_law("BGB", "§ 823")
# equivalent: cases citing "§ 823 BGB"
```

Returns: same dict format as `search_case_law`.

## Supported Courts

| Code    | Name                        |
|---------|-----------------------------|
| BGH     | Bundesgerichtshof           |
| BVERFG  | Bundesverfassungsgericht    |
| BAG     | Bundesarbeitsgericht        |
| BFH     | Bundesfinanzhof             |
| BVERWG  | Bundesverwaltungsgericht    |
| BPATG   | Bundespatentgericht         |

## Data Source

rechtsprechung-im-internet.de — official, free, no rate limits.
Only Leitsatz + Tenor are indexed locally. Volltext is fetched on-demand.

## Combining with lex-retriever

```python
from lex_retriever import search_law
from lex_cases import search_case_law, get_cases_citing_law

# Find the law, then find cases applying it
laws = search_law("Produzentenhaftung")
cases = get_cases_citing_law("BGB", "§ 823")
```

## Agent Rules

- Call `search_case_law` first for semantic search over Leitsätze
- Only call `get_case_fulltext` when the full Tatbestand/Gründe is needed — it's a live HTTP fetch
- Use `get_cases_citing_law` when the user asks about cases applying a specific paragraph
- Combine with `lex_retriever.search_law` to find both the statute and case law in one answer
