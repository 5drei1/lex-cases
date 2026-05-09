# lex-cases — Agent Interface

Semantic search and full-text retrieval over indexed German federal court decisions.

Data source: [rechtsprechung-im-internet.de](https://www.rechtsprechung-im-internet.de) — official, free, publicly usable case law database of the Federal Ministry of Justice.

Supported courts: BVerfG, BGH, BAG, BFH, BVerwG, BPatG.

---

## Available Functions

### search_case_law(query, courts, laws_cited, date_from, date_to, top_k)

Semantic search over indexed Leitsätze (headnotes).

**Parameters:**

| Parameter    | Type             | Default | Description |
|---|---|---|---|
| `query`      | `str`            | required | Natural language query or legal term (German or English) |
| `courts`     | `list[str] \| None` | `None` | Filter by court codes, e.g. `["BGH", "BAG"]`; `None` = all |
| `laws_cited` | `list[str] \| None` | `None` | Filter to decisions citing these statutes, e.g. `["§ 823 BGB"]` |
| `date_from`  | `str \| None`    | `None` | ISO date lower bound, e.g. `"2020-01-01"` |
| `date_to`    | `str \| None`    | `None` | ISO date upper bound, e.g. `"2024-12-31"` |
| `top_k`      | `int`            | `10`   | Number of results |

**Returns:** `list[dict]`

| Key          | Type        | Description |
|---|---|---|
| `court`      | `str`       | Court code, e.g. `"BGH"` |
| `az`         | `str`       | Case reference (Aktenzeichen), e.g. `"IV ZR 123/24"` |
| `date`       | `str`       | Decision date ISO, e.g. `"2024-11-15"` |
| `type`       | `str`       | `"Urteil"` or `"Beschluss"` |
| `leitsatz`   | `str`       | Indexed headnote text |
| `laws_cited` | `list[str]` | Cited statutes extracted from Normkette |
| `score`      | `float`     | Similarity 0.0–1.0 (higher = more relevant) |
| `url`        | `str`       | Link to full decision on rechtsprechung-im-internet.de |

**Example:**
```python
from lex_cases import search_case_law

results = search_case_law(
    "Produzentenhaftung § 823 BGB",
    courts=["BGH"],
    top_k=5,
)
for r in results:
    print(r["court"], r["az"], r["date"], r["score"])
```

**When to use:** Default entry point for unstructured legal queries about court decisions.

---

### get_case_fulltext(url)

Fetch and parse the full decision text (Tatbestand + Entscheidungsgründe) on demand via HTTP.

**Parameters:**

| Parameter | Type  | Description |
|---|---|---|
| `url`     | `str` | URL from a `search_case_law` result |

**Returns:** `str` — Concatenated full text (Tatbestand + Gründe), may be several thousand characters.

**Note:** Makes a live HTTP request to rechtsprechung-im-internet.de. Do not call in bulk; use for individual case deep-dives only.

**Example:**
```python
from lex_cases import search_case_law, get_case_fulltext

results = search_case_law("Produzentenhaftung", courts=["BGH"], top_k=1)
fulltext = get_case_fulltext(results[0]["url"])
print(fulltext[:500])
```

---

### get_cases_citing_law(law, paragraph)

Return all indexed decisions that cite a specific statute paragraph.

**Parameters:**

| Parameter   | Type  | Description |
|---|---|---|
| `law`       | `str` | Law abbreviation, e.g. `"BGB"` |
| `paragraph` | `str` | Paragraph, e.g. `"§ 823"` or `"§ 280"` |

**Returns:** `list[dict]` — Same format as `search_case_law` results, `score` is always `1.0`.

**Example:**
```python
from lex_cases import get_cases_citing_law

results = get_cases_citing_law("BGB", "§ 823")
print(f"{len(results)} decisions cite § 823 BGB")
```

---

## CLI (for setup and maintenance — not for agents)

```bash
python -m lex_cases index BGH          # index one court
python -m lex_cases index-all           # index all six courts
python -m lex_cases status              # show entry counts per court
python -m lex_cases search "query"      # quick CLI search
```

---

## Rules for agents

- Call `search_case_law` for unstructured queries; `get_cases_citing_law` when the statute is known.
- Use `get_case_fulltext` sparingly — one HTTP request per call, not in loops over large result sets.
- Court codes are case-insensitive in the API but conventionally uppercase: `BGH`, `BAG`, `BFH`, etc.
- Dates follow ISO 8601: `"YYYY-MM-DD"`.
- The index only contains Leitsätze and Tenöre — not full Tatbestand/Gründe. Use `get_case_fulltext` to access the complete text.
- The index is populated offline with `python -m lex_cases index-all`. If results are empty, the index may not be initialized.
