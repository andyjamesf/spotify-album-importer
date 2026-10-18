# spotify-album-importer

Saves the albums listed in a CSV file to your Spotify library. Anything not found in the Spotify catalog is skipped and listed in a report. Uses only the Python 3 standard library, no dependencies.

## CSV format

```csv
artist,album
Pink Floyd,The Wall
Tool,Ænima
Queen,
```

A row without an album (like `Queen,`) is only used with `--follow-artists`, which follows the artist.

## Steps

1. **Create a Spotify app.** Go to <https://developer.spotify.com/dashboard>, click *Create app* and fill in the name and description.
2. **Redirect URI:** `http://127.0.0.1:8888/callback`. It must be exactly this, with `127.0.0.1` and not `localhost`.
3. **API:** select only *Web API*, accept the terms and save.
4. **Copy the Client ID** from the app's *Settings*. The Client ID is not secret and this script does not use the Client Secret.
5. **Dry run first, saving nothing:**
   ```
   python3 spotify_album_importer.py example.csv --client-id YOUR_CLIENT_ID --dry-run
   ```
   The browser opens so you can authorize. When it finishes, open `spotify_report.txt` and check that the albums found are the ones you want. Matching is approximate and may pick a different edition (deluxe, remaster) or, rarely, the wrong album.
6. **Run for real,** without `--dry-run`:
   ```
   python3 spotify_album_importer.py my_list.csv --client-id YOUR_CLIENT_ID
   ```
   Add `--follow-artists` to also follow the artists on rows without an album.

Instead of `--client-id` you can set the `SPOTIFY_CLIENT_ID` environment variable.

## Options

| Option | What it does |
|---|---|
| `--client-id` | Client ID of your app (or `SPOTIFY_CLIENT_ID`) |
| `--dry-run` | Only searches and writes the report, does not change your account |
| `--follow-artists` | Follows the artists on rows without an album |
| `--report` | Report path (default `spotify_report.txt`) |

## Notes

- Login uses the OAuth PKCE flow. The token only exists in memory while the script runs and is never written to disk.
- If your app is in *development mode*, only accounts you add under *User Management* can authorize it.
- The script uses `PUT /me/library` and, if your app rejects it, falls back to the older `PUT /me/albums`. Spotify's API has changed recently and may change again.
- To move your library to Apple Music, services like Soundiiz can transfer between platforms. Not tested here.

## License

MIT
