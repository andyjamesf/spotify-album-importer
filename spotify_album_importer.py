#!/usr/bin/env python3
"""Save the albums listed in a CSV (columns: artist,album) to your Spotify library."""
import argparse, base64, csv, hashlib, http.server, json, os, re, secrets, sys, time
import unicodedata, urllib.error, urllib.parse, urllib.request, webbrowser

REDIRECT = "http://127.0.0.1:8888/callback"
SCOPE = "user-library-modify user-follow-modify"
API = "https://api.spotify.com/v1"


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def login(client_id):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT,
        "scope": SCOPE, "code_challenge_method": "S256", "code_challenge": challenge})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got["code"] = q.get("code", [None])[0]
            self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers()
            self.wfile.write("Done, you can close this window.".encode())
        def log_message(self, format, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 8888), H)
    print("Opening the browser to authorize... if it does not open, go to:\n" + url)
    webbrowser.open(url)
    srv.handle_request()
    if not got.get("code"):
        sys.exit("Authorization failed.")
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": REDIRECT,
        "client_id": client_id, "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://accounts.spotify.com/api/token", data)) as r:
        return json.load(r)["access_token"]


def call(token, method, path, params=None, body=None, retries=5):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    for _ in range(retries):
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "5")) + 1); continue
            raise
    raise RuntimeError("too many 429 responses")


def find_album(token, artist, album):
    for q in (f'album:"{album}" artist:"{artist}"', f"{album} {artist}"):
        res = call(token, "GET", "/search", {"q": q, "type": "album", "limit": 10})
        for it in res.get("albums", {}).get("items", []):
            if it.get("album_type") == "single" and norm(album) != norm(it["name"]):
                continue
            names = [norm(a["name"]) for a in it["artists"]]
            if norm(artist) in names or any(norm(artist) in n for n in names):
                a, b = norm(album), norm(it["name"])
                if a == b or a in b or b in a:
                    return it
    return None


def find_artist(token, artist):
    res = call(token, "GET", "/search", {"q": artist, "type": "artist", "limit": 5})
    for it in res.get("artists", {}).get("items", []):
        if norm(it["name"]) == norm(artist):
            return it
    return None


def save(token, kind, ids):
    """kind: 'album' or 'artist'. Tries the new endpoint (/me/library), then the old one."""
    for i in range(0, len(ids), 20):
        batch = ids[i:i + 20]
        uris = ",".join(f"spotify:{kind}:{x}" for x in batch)
        try:
            call(token, "PUT", "/me/library", {"uris": uris})
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404, 410):
                raise
            if kind == "album":
                call(token, "PUT", "/me/albums", body={"ids": batch})
            else:
                call(token, "PUT", "/me/following", {"type": "artist", "ids": ",".join(batch)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="CSV file with the columns artist,album")
    ap.add_argument("--client-id", default=os.environ.get("SPOTIFY_CLIENT_ID"),
                    help="Client ID of your Spotify app (or the SPOTIFY_CLIENT_ID variable)")
    ap.add_argument("--dry-run", action="store_true", help="only search and write the report, save nothing")
    ap.add_argument("--follow-artists", action="store_true", help="also follow the artists on rows without an album")
    ap.add_argument("--report", default="spotify_report.txt", help="where to write the report")
    a = ap.parse_args()
    if not a.client_id:
        sys.exit("Missing Client ID (--client-id or SPOTIFY_CLIENT_ID).")

    token = login(a.client_id)
    with open(a.csv, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    albums, artists, missing = {}, {}, []
    for l in rows:
        art, alb = (l.get("artist") or "").strip(), (l.get("album") or "").strip()
        if alb:
            it = find_album(token, art, alb)
            if it:
                albums[it["id"]] = f'{art} - {alb}  ->  {it["name"]}'
            else:
                missing.append(f"{art} - {alb}")
        elif a.follow_artists:
            it = find_artist(token, art)
            if it:
                artists[it["id"]] = art
            else:
                missing.append(f"{art} (artist)")
        print(f'\r{len(albums)} albums, {len(artists)} artists, {len(missing)} not found', end="", flush=True)
    print()

    if not a.dry_run:
        save(token, "album", list(albums))
        if artists:
            save(token, "artist", list(artists))
    with open(a.report, "w", encoding="utf-8") as f:
        f.write("FOUND\n" + "\n".join(albums.values()) + "\n\nNOT FOUND\n" + "\n".join(missing) + "\n")
    print(("Dry run: nothing was saved. " if a.dry_run else "Saved. ") + f"Report in {a.report}")


if __name__ == "__main__":
    main()
