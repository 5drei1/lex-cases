"""CLI entry point: python -m lex_cases <command> [args]"""

import argparse
import sys


def _cmd_index(args: argparse.Namespace) -> None:
    from .indexer import index_court
    index_court(args.court.upper())


def _cmd_index_all(_args: argparse.Namespace) -> None:
    from .indexer import index_all_courts
    index_all_courts()


def _cmd_status(_args: argparse.Namespace) -> None:
    from .indexer import index_status
    status = index_status()
    for court, count in status.items():
        print(f"{court:8s} {count:>6} entries")


def _cmd_search(args: argparse.Namespace) -> None:
    from .tool import search_case_law
    courts = args.courts.split(",") if args.courts else None
    results = search_case_law(args.query, courts=courts, top_k=args.top_k)
    for r in results:
        print(f"[{r['score']:.3f}] {r['court']} {r['az']} ({r['date']})")
        print(f"  {r['leitsatz'][:120]}...")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(prog="lex_cases")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index one court")
    p_index.add_argument("court", help="Court code, e.g. BGH")
    p_index.set_defaults(func=_cmd_index)

    p_all = sub.add_parser("index-all", help="Index all courts")
    p_all.set_defaults(func=_cmd_index_all)

    p_status = sub.add_parser("status", help="Show index entry counts per court")
    p_status.set_defaults(func=_cmd_status)

    p_search = sub.add_parser("search", help="Semantic search over case law")
    p_search.add_argument("query")
    p_search.add_argument("--courts", help="Comma-separated court codes, e.g. BGH,BAG")
    p_search.add_argument("--top-k", type=int, default=10)
    p_search.set_defaults(func=_cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
