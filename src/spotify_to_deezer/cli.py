"""Interface en ligne de commande pour la migration."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import AppConfig
from .deezer_client import DeezerService
from .spotify_client import SpotifyService
from .sync import DeezerToSpotifyMigrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migre playlists et favoris Deezer vers Spotify",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--favorites-only",
        action="store_true",
        help="Ne migrer que les coups de cœur",
    )
    group.add_argument(
        "--playlists-only",
        action="store_true",
        help="Ne migrer que les playlists",
    )
    parser.add_argument(
        "--market",
        default=None,
        help="Code pays ISO 3166-1 alpha-2 utilisé pour la recherche Spotify (par défaut USER_COUNTRY)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Niveau de verbosité",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    try:
        config = AppConfig.from_env()
    except RuntimeError as exc:
        parser.error(str(exc))
        return 1

    deezer = DeezerService(config.deezer_access_token)
    spotify = SpotifyService(
        client_id=config.spotify_client_id,
        client_secret=config.spotify_client_secret,
        redirect_uri=config.spotify_redirect_uri,
        refresh_token=config.spotify_refresh_token,
    )
    migrator = DeezerToSpotifyMigrator(
        deezer=deezer,
        spotify=spotify,
        market=args.market or config.user_country,
    )

    if args.favorites_only:
        migrator.migrate_favorites(deezer.fetch_favorite_tracks())
    elif args.playlists_only:
        for playlist in deezer.fetch_playlists():
            migrator.migrate_playlist(playlist)
    else:
        migrator.migrate_all()

    return 0


if __name__ == "__main__":  # pragma: no cover - pour exécution directe
    sys.exit(main())
