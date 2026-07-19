from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from fminside.config import DEFAULT_MAX_LOAD_MORE, DEFAULT_MAX_PROFILES, OUTPUT_DIR
from fminside.pipeline import ScrapeFilters, run_scrape


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scraper FMInside → JSON GoFoot (por clube ou liga).",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--club", help='Nome exato do clube no fminside (ex: "Real Madrid")')
    g.add_argument(
        "--league",
        help='Nome exato da liga no fminside (ex: "Premier League", "Série A")',
    )
    p.add_argument(
        "--nation",
        "--nationality",
        dest="nationality",
        default="",
        help=(
            'País da competição (ex: "Brazil", "Italy") — não é a nacionalidade '
            "do jogador. Recomendado com --league quando o nome se repete "
            '(ex: Série A BR vs Serie A IT).'
        ),
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_LOAD_MORE,
        help="Limite de load-more (omitir = sem limite)",
    )
    p.add_argument(
        "--max-players",
        type=int,
        default=DEFAULT_MAX_PROFILES,
        help="Limite de perfis (omitir = todos)",
    )
    p.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_DIR),
        help="Diretório de saída (default: output/)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    args = build_parser().parse_args(argv)

    if args.league and not args.nationality:
        logging.warning(
            "Liga sem --nation: nomes iguais (ex. Série A) podem misturar países. "
            'Prefira: --league "Série A" --nation "Brazil"'
        )

    filters = ScrapeFilters(
        club=args.club or "",
        league=args.league or "",
        nationality=args.nationality or "",
        max_load_more=args.max_pages,
        max_profiles=args.max_players,
        output_dir=Path(args.output),
    )
    result = run_scrape(filters)
    print(f"\nOK: {len(result.jogadores)} jogadores")
    print(f"Arquivos em: {result.output_dir}")
    for f in result.files:
        print(f"  - {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
