"""Gestion de la configuration de l'application."""

from __future__ import annotations

import dataclasses
import os
from typing import Optional

from dotenv import load_dotenv


def _load_env() -> None:
    """Charge les variables d'environnement depuis un fichier `.env` si présent."""

    if not getattr(_load_env, "_loaded", False):  # type: ignore[attr-defined]
        load_dotenv()
        _load_env._loaded = True  # type: ignore[attr-defined]


@dataclasses.dataclass(slots=True)
class AppConfig:
    """Paramètres de connexion pour Deezer et Spotify."""

    deezer_access_token: str
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str
    spotify_refresh_token: str
    user_country: str = "FR"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Construit la configuration depuis les variables d'environnement."""

        _load_env()
        missing: list[str] = []

        def require(name: str) -> str:
            value = os.getenv(name)
            if not value:
                missing.append(name)
                return ""
            return value

        config = cls(
            deezer_access_token=require("DEEZER_ACCESS_TOKEN"),
            spotify_client_id=require("SPOTIFY_CLIENT_ID"),
            spotify_client_secret=require("SPOTIFY_CLIENT_SECRET"),
            spotify_redirect_uri=require("SPOTIFY_REDIRECT_URI"),
            spotify_refresh_token=require("SPOTIFY_REFRESH_TOKEN"),
            user_country=os.getenv("USER_COUNTRY", "FR"),
        )

        if missing:
            raise RuntimeError(
                "Variables d'environnement manquantes: " + ", ".join(sorted(missing))
            )

        return config

    @classmethod
    def optional_from_env(cls) -> Optional["AppConfig"]:
        """Version permissive retournant ``None`` si un champ obligatoire manque."""

        try:
            return cls.from_env()
        except RuntimeError:
            return None
