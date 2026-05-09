"""CLI for lex-cases: index, status, search."""

from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lex-cases",
        description="Semantische Suche über deutsche Gerichtsurteile",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index a single court")
    p_index.add_argument(
        "court",
        choices=["BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"],
        help="Court code to index",
    )

    sub.add_parser("index-all", help="Index all 6 federal courts")
    sub.add_parser("status", help="Show index stats per court")

    p_search = sub.add_parser("search", help="Search court decisions")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument(
        "-c", "--court",
        action="append",
        dest="courts",
        metavar="COURT",
        help="Filter by court (repeatable)",
    )
    p_search.add_argument(
        "-l", "--laws",
        action="append",
        dest="laws_cited",
        metavar="LAW",
        help="Filter by laws_cited substring (repeatable)",
    )
    p_search.add_argument("-k", "--top-k", type=int, default=10, help="Number of results")
    p_search.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.command == "index":
        _cmd_index(args.court)
    elif args.command == "index-all":
        _cmd_index_all()
    elif args.command == "status":
        _cmd_status()
    elif args.command == "search":
        _cmd_search(args.query, args.courts, args.laws_cited, args.top_k, args.json)


def _cmd_index(court: str) -> None:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from .indexer import index_court
    n = index_court(court)
    print(f"Indexed {n} new chunks for {court}.")


def _cmd_index_all() -> None:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from .indexer import index_all_courts
    results = index_all_courts()
    for court, n in results.items():
        print(f"  {court}: {n} new chunks")


def _cmd_status() -> None:
    from .indexer import get_index_stats
    stats = get_index_stats()
    if not stats:
        print("No index found. Run: python -m lex_cases index-all")
        return
    total = sum(stats.values())
    print(f"{'Court':<10} {'Chunks':>8}")
    print("-" * 20)
    for court in ["BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"]:
        count = stats.get(court, 0)
        print(f"{court:<10} {count:>8}")
    print("-" * 20)
    print(f"{'TOTAL':<10} {total:>8}")


def _cmd_search(
    query: str,
    courts: list[str] | None,
    laws_cited: list[str] | None,
    top_k: int,
    as_json: bool,
) -> None:
    from .retriever import LexCaseRetriever
    r = LexCaseRetriever()
    results = r.search(query, courts=courts, laws_cited=laws_cited, top_k=top_k)
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    if not results:
        print("No results found.")
        return
    for i, res in enumerate(results, 1):
        print(f"\n{'─' * 60}")
        print(f"[{i}] {res['court']} · {res['az']} · {res['date']} · {res['type']}")
        print(f"    Score: {res['score']:.3f}")
        if res.get("leitsatz"):
            leitsatz = res["leitsatz"]
            print(f"    Leitsatz: {leitsatz[:200]}{'...' if len(leitsatz) > 200 else ''}")
        if res.get("laws_cited"):
            print(f"    Laws: {', '.join(res['laws_cited'][:5])}")
        print(f"    URL: {res['url']}")


if __name__ == "__main__":
    main()
