# SpotifyToDeezer

Outil en ligne de commande pour migrer automatiquement vos playlists et vos coups de cœur depuis Deezer vers Spotify.

## Fonctionnalités

- Authentification via les API officielles Deezer et Spotify (OAuth).
- Récupération de toutes les playlists Deezer de l'utilisateur connecté.
- Migration des titres favoris ("coups de cœur") Deezer vers la bibliothèque Spotify.
- Création des playlists manquantes sur Spotify et ajout des morceaux correspondants.
- Correspondance des titres via leur code ISRC lorsqu'il est disponible, ou à défaut via une recherche texte.

## Pré-requis

1. **Compte développeur Deezer** : créez une application afin d'obtenir un token d'accès utilisateur. Reportez-vous à la [documentation Deezer](https://developers.deezer.com/api/oauth) pour générer un `DEEZER_ACCESS_TOKEN` avec le scope `manage_library`.
2. **Compte développeur Spotify** : créez une application sur <https://developer.spotify.com/dashboard>. Configurez une URL de redirection (par exemple `http://localhost:8080/callback`). Récupérez :
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `SPOTIFY_REDIRECT_URI` (la même que déclarée sur le dashboard)

   Effectuez ensuite une autorisation OAuth (scopes `playlist-read-private playlist-modify-public playlist-modify-private user-library-read user-library-modify`). Conservez le `refresh_token` retourné et renseignez-le dans `SPOTIFY_REFRESH_TOKEN`.
3. **Python 3.10+**.

Créez un fichier `.env` à la racine du projet avec les variables suivantes :

```ini
DEEZER_ACCESS_TOKEN=...
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=...
SPOTIFY_REFRESH_TOKEN=...
# Optionnel : code pays ISO utilisé pour la recherche Spotify (défaut FR)
USER_COUNTRY=FR
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Utilisation

La commande principale est installée sous le nom `spotify-to-deezer` :

```bash
spotify-to-deezer
```

Options disponibles :

- `--favorites-only` : ne migre que les coups de cœur Deezer vers les titres "likés" Spotify.
- `--playlists-only` : ne migre que les playlists Deezer.
- `--market` : force le marché Spotify utilisé lors de la recherche des morceaux (sinon `USER_COUNTRY`).
- `--log-level` : change la verbosité (`DEBUG`, `INFO`, `WARNING`, `ERROR`).

## Architecture

- `spotify_to_deezer/config.py` : lecture de la configuration et des variables d'environnement.
- `spotify_to_deezer/deezer_client.py` : récupération des playlists et favoris via l'API REST Deezer.
- `spotify_to_deezer/spotify_client.py` : encapsulation de Spotipy pour la création de playlists et la sauvegarde des titres.
- `spotify_to_deezer/sync.py` : logique métier réalisant la correspondance et l'import des morceaux.
- `spotify_to_deezer/cli.py` : interface en ligne de commande.

## Limitations connues

- La qualité de la correspondance dépend des métadonnées Deezer. Certains titres rares peuvent ne pas être trouvés sur Spotify.
- Le script suppose un `refresh_token` Spotify valide. Relancez une autorisation OAuth si l'API retourne une erreur 401.
- La migration ne supprime ni ne remplace les playlists existantes sur Spotify : les morceaux migrés sont ajoutés à la suite.

## Contribution

Les contributions sont les bienvenues ! Ouvrez une issue ou une pull request pour proposer des améliorations.
