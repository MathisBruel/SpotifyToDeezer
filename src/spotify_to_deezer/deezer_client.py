"""Client simplifié pour l'API Deezer."""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import Iterator
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://api.deezer.com"


class DeezerError(RuntimeError):
    """Erreur retournée par l'API Deezer."""


@dataclasses.dataclass(slots=True)
class DeezerTrack:
    """Représentation locale d'un morceau Deezer."""

    id: int
    title: str
    artist_name: str
    album_name: str
    duration: int
    isrc: Optional[str]


@dataclasses.dataclass(slots=True)
class DeezerPlaylist:
    """Représentation locale d'une playlist Deezer."""

    id: int
    title: str
    description: str
    is_public: bool
    tracks: List[DeezerTrack]


class DeezerService:
    """Accès aux données Deezer de l'utilisateur."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def _request(self, method: str, path: str, **params: Any) -> Dict[str, Any]:
        url = f"{API_BASE_URL}{path}"
        response = requests.request(
            method,
            url,
            params={"access_token": self._access_token, **params},
            timeout=30,
        )
        if response.status_code != 200:
            raise DeezerError(f"Erreur HTTP {response.status_code}: {response.text}")
        data = response.json()
        if "error" in data:
            error = data["error"]
            raise DeezerError(
                f"Erreur Deezer {error.get('code')}: {error.get('message', 'inconnue')}"
            )
        return data

    def _paginate(self, path: str, **params: Any) -> Iterator[Dict[str, Any]]:
        index = 0
        while True:
            batch = self._request("GET", path, index=index, limit=50, **params)
            data = batch.get("data", [])
            if not data:
                break
            yield from data
            next_url = batch.get("next")
            if not next_url:
                break
            index += 50

    def fetch_user_id(self) -> int:
        """Retourne l'identifiant numérique de l'utilisateur connecté."""

        data = self._request("GET", "/user/me")
        user_id = data.get("id")
        if not isinstance(user_id, int):
            raise DeezerError("Impossible de récupérer l'identifiant utilisateur")
        return user_id

    def fetch_favorite_tracks(self) -> List[DeezerTrack]:
        """Récupère la liste complète des coups de cœur."""

        tracks: List[DeezerTrack] = []
        for raw in self._paginate("/user/me/tracks"):
            tracks.append(self._parse_track(raw))
        LOGGER.info("%s favoris Deezer récupérés", len(tracks))
        return tracks

    def fetch_playlists(self) -> List[DeezerPlaylist]:
        """Récupère l'ensemble des playlists de l'utilisateur."""

        playlists: List[DeezerPlaylist] = []
        for raw_playlist in self._paginate("/user/me/playlists"):
            playlist_id = raw_playlist["id"]
            details = self._request("GET", f"/playlist/{playlist_id}")
            playlist_tracks = [
                self._parse_track(track)
                for track in details.get("tracks", {}).get("data", [])
            ]
            playlists.append(
                DeezerPlaylist(
                    id=playlist_id,
                    title=details.get("title", raw_playlist.get("title", "")),
                    description=details.get("description", ""),
                    is_public=bool(details.get("public", False)),
                    tracks=playlist_tracks,
                )
            )
        LOGGER.info("%s playlists Deezer récupérées", len(playlists))
        return playlists

    @staticmethod
    def _parse_track(raw: Dict[str, Any]) -> DeezerTrack:
        artist = raw.get("artist", {}) or {}
        album = raw.get("album", {}) or {}
        isrc = raw.get("isrc") or album.get("upc")
        return DeezerTrack(
            id=int(raw.get("id", 0)),
            title=str(raw.get("title", "")),
            artist_name=str(artist.get("name", "")),
            album_name=str(album.get("title", "")),
            duration=int(raw.get("duration", 0)),
            isrc=isrc or None,
        )
