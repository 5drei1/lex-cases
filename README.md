# lex-cases

Semantic search over German federal court decisions (Gerichtsurteile).

Sister tool to [lex-retriever](https://github.com/5drei1/lex-retriever).

## Data source

[rechtsprechung-im-internet.de](https://www.rechtsprechung-im-internet.de) — official, free, publicly usable case law database of the Federal Ministry of Justice.

Courts: BVerfG, BGH, BAG, BFH, BVerwG, BPatG.

## Usage

```python
from lex_cases import search_case_law, get_case_fulltext, get_cases_citing_law

results = search_case_law("Produzentenhaftung § 823 BGB", courts=["BGH"])
```

## CLI

```bash
python -m lex_cases index BGH
python -m lex_cases index-all
python -m lex_cases status
python -m lex_cases search "Produzentenhaftung § 823 BGB"
```

## License

MIT
