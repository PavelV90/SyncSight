"""Command line entry point: `syncsight-ingest <source> [options]`."""

import argparse
import logging
from collections.abc import Sequence
from datetime import date, timedelta

import httpx2
from sqlalchemy.orm import Session

from syncsight.db.models import IngestRun
from syncsight.db.session import make_engine
from syncsight.ingestion import medicines, permits, shab, swissmedic, web, zefix_lindas
from syncsight.ingestion.http import make_client
from syncsight.ingestion.normalize import normalize_uid


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx2").setLevel(logging.WARNING)  # one line per request is too noisy
    engine = make_engine()
    with Session(engine) as session, make_client() as client:
        _run(args, session, client)
        # reached only when the command succeeded
        session.add(IngestRun(source=_RUN_SOURCES.get(args.source, args.source)))
        session.commit()
    engine.dispose()


# commands that refresh the same source as another command
_RUN_SOURCES = {"shab-swissmedic": "shab", "match": "swissmedic", "reclassify": "shab"}


def _run(args: argparse.Namespace, session: Session, client: httpx2.Client) -> None:
    if args.source == "zefix":
        zefix_lindas.run(session, client, cantons=args.canton)
    elif args.source == "shab" and args.uid:
        for uid in args.uid:
            shab.run(session, client, keyword=uid, delay=args.delay)
    elif args.source == "shab":
        shab.run(session, client, since=args.since, until=args.until, delay=args.delay)
    elif args.source == "shab-swissmedic":
        uids = swissmedic.matched_uids(session)
        logging.info("shab: history of %d Swissmedic-licensed companies", len(uids))
        for uid in uids:
            shab.run(session, client, keyword=uid, delay=args.delay)
    elif args.source == "swissmedic":
        swissmedic.run(session, client)
    elif args.source == "permits":
        targets = args.uid or swissmedic.matched_uids(session)
        permits.run(session, client, targets, since=args.since, delay=args.delay)
    elif args.source in ("websites", "crawl"):
        targets = args.uid or swissmedic.matched_uids(session)
        if args.source == "websites":
            web.resolve_websites(session, client, targets)
        else:
            web.crawl(session, targets)
    elif args.source == "medicines":
        medicines.run(session, client)
    elif args.source == "reclassify":
        changed = shab.reclassify(session)
        logging.info("shab: %d notices relabelled", changed)
    elif args.source == "match":
        matched = swissmedic.match_companies(session)
        session.commit()
        logging.info("swissmedic: %d holders matched", matched)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="syncsight-ingest", description=__doc__)
    sources = parser.add_subparsers(dest="source", required=True)

    zefix = sources.add_parser("zefix", help="active companies from Zefix via LINDAS")
    zefix.add_argument(
        "--canton", action="append", choices=zefix_lindas.CANTONS, help="repeatable; default all"
    )

    yesterday = date.today() - timedelta(days=1)
    notices = sources.add_parser("shab", help="SHAB/SOGC register notices")
    notices.add_argument("--since", type=date.fromisoformat, default=yesterday)
    notices.add_argument("--until", type=date.fromisoformat, default=date.today())
    notices.add_argument(
        "--uid", action="append", type=_uid, help="full history of one company (repeatable)"
    )
    notices.add_argument("--delay", type=float, default=0.2, help="seconds between requests")

    history = sources.add_parser(
        "shab-swissmedic", help="SHAB history of all companies matched to a Swissmedic licence"
    )
    history.add_argument("--delay", type=float, default=0.2, help="seconds between requests")

    sources.add_parser("swissmedic", help="Swissmedic establishment licences (full snapshot)")
    sources.add_parser("medicines", help="Swissmedic authorised medicinal products (snapshot)")

    building = sources.add_parser(
        "permits", help="building permits filed by Swissmedic-licensed companies (or --uid)"
    )
    building.add_argument(
        "--since", type=date.fromisoformat, default=date.today() - timedelta(days=730)
    )
    building.add_argument("--uid", action="append", type=_uid, help="repeatable")
    building.add_argument("--delay", type=float, default=0.2, help="seconds between requests")
    for name, text in (
        ("websites", "find and verify websites of Swissmedic-licensed companies (or --uid)"),
        ("crawl", "scan their websites, feeds and career pages for MES keywords (or --uid)"),
    ):
        sources.add_parser(name, help=text).add_argument(
            "--uid", action="append", type=_uid, help="repeatable"
        )
    sources.add_parser("match", help="re-match Swissmedic licence holders to companies")
    sources.add_parser("reclassify", help="re-apply SHAB text rules to stored notices")
    return parser


def _uid(value: str) -> str:
    uid = normalize_uid(value)
    if uid is None:
        raise argparse.ArgumentTypeError(f"not a UID: {value}")
    return uid


if __name__ == "__main__":
    main()
