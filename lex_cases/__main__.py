import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="lex-cases", description="Semantische Suche über deutsche Gerichtsurteile")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Index a single court")
    p_index.add_argument("court", choices=["BGH", "BVERFG", "BAG", "BFH", "BVERWG", "BPATG"])

    sub.add_parser("index-all", help="Index all 6 federal courts")
    sub.add_parser("status", help="Show index stats per court")

    p_search = sub.add_parser("search", help="Search court decisions")
    p_search.add_argument("query")
    p_search.add_argument("-c", "--court", action="append", dest="courts", metavar="COURT")
    p_search.add_argument("-l", "--laws", action="append", dest="laws_cited", metavar="LAW")
    p_search.add_argument("-k", "--top-k", type=int, default=10)

    args = parser.parse_args()

    if args.command == "index":
        from .indexer import index_court
        index_court(args.court)
    elif args.command == "index-all":
        from .indexer import index_all_courts
        index_all_courts()
    elif args.command == "status":
        _cmd_status()
    elif args.command == "search":
        _cmd_search(args.query, args.courts, args.laws_cited, args.top_k)


def _cmd_status() -> None:
    raise NotImplementedError("status command — implemented in SUB-5")


def _cmd_search(query: str, courts, laws_cited, top_k: int) -> None:
    raise NotImplementedError("search command — implemented in SUB-5")


if __name__ == "__main__":
    main()
