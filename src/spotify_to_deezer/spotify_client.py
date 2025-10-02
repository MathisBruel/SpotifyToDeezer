"""Client Spotify pour la migration."""

from __future__ import annotations

import logging
import time
from typing import Dict, Iterable, List, Optional

import requests
import spotipy

LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"


class SpotifyError(RuntimeError):
    """Erreur liée à l'API Spotify."""


class SpotifyService:
    """Client de haut niveau encapsulant Spotipy."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        refresh_token: str,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._refresh_token = refresh_token
        self._access_token: Optional[str] = None
        self._expires_at: float = 0
        self._client: Optional[spotipy.Spotify] = None
        self._user_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Gestion du token
    # ------------------------------------------------------------------
    def _refresh_access_token(self) -> None:
        LOGGER.debug("Renouvellement du token Spotify")
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "redirect_uri": self._redirect_uri,
            },
            auth=(self._client_id, self._client_secret),
            timeout=30,
        )
        if response.status_code != 200:
            raise SpotifyError(
                f"Échec du renouvellement du token Spotify: {response.status_code} {response.text}"
            )
        payload = response.json()
        self._access_token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._expires_at = time.time() + expires_in - 30
        LOGGER.debug("Token Spotify renouvelé (expiration dans %ss)", expires_in)

    def _ensure_client(self) -> spotipy.Spotify:
        if not self._access_token or time.time() >= self._expires_at:
            self._refresh_access_token()
            self._client = None
        if self._client is None:
            self._client = spotipy.Spotify(auth=self._access_token)
        return self._client

    # ------------------------------------------------------------------
    # Informations utilisateur
    # ------------------------------------------------------------------
    def current_user_id(self) -> str:
        if self._user_id:
            return self._user_id
        client = self._ensure_client()
        me = client.current_user()
        user_id = me.get("id")
        if not user_id:
            raise SpotifyError("Impossible de récupérer l'ID utilisateur Spotify")
        self._user_id = user_id
        return user_id

    # ------------------------------------------------------------------
    # Playlists
    # ------------------------------------------------------------------
    def ensure_playlist(
        self, name: str, description: str, public: bool
    ) -> Dict[str, str]:
        client = self._ensure_client()
        playlist = self._find_playlist_by_name(name)
        if playlist:
            LOGGER.info("Playlist Spotify existante: %s", name)
            if description and playlist.get("description") != description:
                client.playlist_change_details(
                    playlist_id=playlist["id"],
                    description=description,
                    public=public,
                )
            return playlist

        LOGGER.info("Création de la playlist Spotify: %s", name)
        created = client.user_playlist_create(
            user=self.current_user_id(),
            name=name,
            public=public,
            description=description,
        )
        return created

    def _find_playlist_by_name(self, name: str) -> Optional[Dict[str, str]]:
        client = self._ensure_client()
        results = client.current_user_playlists(limit=50)
        while results:
            for item in results.get("items", []):
                if item.get("name") == name:
                    return item
            results = client.next(results) if results.get("next") else None
        return None

    def add_tracks_to_playlist(self, playlist_id: str, track_ids: Iterable[str]) -> None:
        client = self._ensure_client()
        batch: List[str] = []
        for track_id in track_ids:
            batch.append(track_id)
            if len(batch) == 100:
                client.playlist_add_items(playlist_id, batch)
                batch.clear()
        if batch:
            client.playlist_add_items(playlist_id, batch)

    # ------------------------------------------------------------------
    # Titres favoris
    # ------------------------------------------------------------------
    def save_tracks(self, track_ids: Iterable[str]) -> None:
        client = self._ensure_client()
        batch: List[str] = []
        for track_id in track_ids:
            batch.append(track_id)
            if len(batch) == 50:
                client.current_user_saved_tracks_add(tracks=batch)
                batch.clear()
        if batch:
            client.current_user_saved_tracks_add(tracks=batch)

    # ------------------------------------------------------------------
    # Recherche de titres
    # ------------------------------------------------------------------
    def find_track_id(
        self,
        *,
        isrc: Optional[str],
        title: str,
        artist: str,
        album: Optional[str] = None,
        market: str = "FR",
    ) -> Optional[str]:
        client = self._ensure_client()
        if isrc:
            query = f"isrc:{isrc}"
            LOGGER.debug("Recherche Spotify par ISRC: %s", query)
            result = client.search(q=query, type="track", limit=1, market=market)
            items = result.get("tracks", {}).get("items", [])
            if items:
                return items[0]["id"]

        query_parts = [title]
        if artist:
            query_parts.append(artist)
        if album:
            query_parts.append(album)
        query = " ".join(part for part in query_parts if part)
        if not query:
            return None
        LOGGER.debug("Recherche Spotify texte: %s", query)
        result = client.search(q=query, type="track", limit=5, market=market)
        items = result.get("tracks", {}).get("items", [])
        if not items:
            return None

        normalized_artist = artist.lower()
        for item in items:
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            if normalized_artist and normalized_artist not in artists.lower():
                continue
            return item["id"]
        return items[0]["id"]
