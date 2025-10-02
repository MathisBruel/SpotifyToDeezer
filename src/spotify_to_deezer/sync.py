"""Logique de migration Deezer vers Spotify."""

from __future__ import annotations

import logging
from typing import Iterable, Sequence

from .deezer_client import DeezerPlaylist, DeezerService, DeezerTrack
from .spotify_client import SpotifyService

LOGGER = logging.getLogger(__name__)


class DeezerToSpotifyMigrator:
    """Coordonne les opérations de migration."""

    def __init__(
        self,
        deezer: DeezerService,
        spotify: SpotifyService,
        *,
        market: str = "FR",
    ) -> None:
        self._deezer = deezer
        self._spotify = spotify
        self._market = market

    # ------------------------------------------------------------------
    # Migration principale
    # ------------------------------------------------------------------
    def migrate_all(self) -> None:
        LOGGER.info("Démarrage de la migration complète")
        favorites = self._deezer.fetch_favorite_tracks()
        self.migrate_favorites(favorites)

        playlists = self._deezer.fetch_playlists()
        for playlist in playlists:
            self.migrate_playlist(playlist)

    # ------------------------------------------------------------------
    # Favoris
    # ------------------------------------------------------------------
    def migrate_favorites(self, tracks: Sequence[DeezerTrack]) -> None:
        LOGGER.info("Migration des coups de cœur (%s titres)", len(tracks))
        track_ids = list(self._map_tracks(tracks))
        if not track_ids:
            LOGGER.warning("Aucun favori n'a pu être associé sur Spotify")
            return
        self._spotify.save_tracks(track_ids)
        LOGGER.info("%s favoris ajoutés à Spotify", len(track_ids))

    # ------------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------------
    def migrate_playlist(self, playlist: DeezerPlaylist) -> None:
        LOGGER.info("Migration de la playlist '%s' (%s titres)", playlist.title, len(playlist.tracks))
        track_ids = list(self._map_tracks(playlist.tracks))
        if not track_ids:
            LOGGER.warning(
                "Playlist '%s' ignorée car aucun titre n'a été trouvé sur Spotify",
                playlist.title,
            )
            return
        spotify_playlist = self._spotify.ensure_playlist(
            name=playlist.title,
            description=playlist.description,
            public=playlist.is_public,
        )
        self._spotify.add_tracks_to_playlist(spotify_playlist["id"], track_ids)
        LOGGER.info(
            "Playlist '%s' synchronisée sur Spotify (%s titres)",
            playlist.title,
            len(track_ids),
        )

    # ------------------------------------------------------------------
    # Conversion des titres
    # ------------------------------------------------------------------
    def _map_tracks(self, tracks: Iterable[DeezerTrack]) -> Iterable[str]:
        seen: set[str] = set()
        for track in tracks:
            track_id = self._spotify.find_track_id(
                isrc=track.isrc,
                title=track.title,
                artist=track.artist_name,
                album=track.album_name,
                market=self._market,
            )
            if not track_id:
                LOGGER.warning(
                    "Titre introuvable sur Spotify: %s - %s",
                    track.artist_name,
                    track.title,
                )
                continue
            if track_id in seen:
                continue
            seen.add(track_id)
            yield track_id
