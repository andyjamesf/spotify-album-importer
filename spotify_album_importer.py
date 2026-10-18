#!/usr/bin/env python3
"""Guarda na biblioteca do Spotify os álbuns de um CSV (colunas: artista,album)."""
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
            self.wfile.write("Pronto, já podes fechar esta janela.".encode())
        def log_message(self, format, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 8888), H)
    print("A abrir o browser para autorizar... se não abrir, vai a:\n" + url)
    webbrowser.open(url)
    srv.handle_request()
    if not got.get("code"):
        sys.exit("Autorização falhou.")
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": got["code"], "redirect_uri": REDIRECT,
        "client_id": client_id, "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://accounts.spotify.com/api/token", data)) as r:
        return json.load(r)["access_token"]


def call(token, method, path, params=None, body=None, tentativas=5):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    for _ in range(tentativas):
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
    raise RuntimeError("demasiados 429")


def procurar(token, artista, album):
    for q in (f'album:"{album}" artist:"{artista}"', f"{album} {artista}"):
        res = call(token, "GET", "/search", {"q": q, "type": "album", "limit": 10})
        for it in res.get("albums", {}).get("items", []):
            if it.get("album_type") == "single" and norm(album) != norm(it["name"]):
                continue
            nomes = [norm(a["name"]) for a in it["artists"]]
            if norm(artista) in nomes or any(norm(artista) in n for n in nomes):
                a, b = norm(album), norm(it["name"])
                if a == b or a in b or b in a:
                    return it
    return None


def procurar_artista(token, artista):
    res = call(token, "GET", "/search", {"q": artista, "type": "artist", "limit": 5})
    for it in res.get("artists", {}).get("items", []):
        if norm(it["name"]) == norm(artista):
            return it
    return None


def guardar(token, tipo, ids):
    """tipo: 'album' ou 'artist'. Tenta o endpoint novo (/me/library) e depois o antigo."""
    for i in range(0, len(ids), 20):
        lote = ids[i:i + 20]
        uris = ",".join(f"spotify:{tipo}:{x}" for x in lote)
        try:
            call(token, "PUT", "/me/library", {"uris": uris})
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404, 410):
                raise
            if tipo == "album":
                call(token, "PUT", "/me/albums", body={"ids": lote})
            else:
                call(token, "PUT", "/me/following", {"type": "artist", "ids": ",".join(lote)})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="ficheiro CSV com as colunas artista,album")
    ap.add_argument("--client-id", default=os.environ.get("SPOTIFY_CLIENT_ID"),
                    help="Client ID da tua app Spotify (ou variável SPOTIFY_CLIENT_ID)")
    ap.add_argument("--teste", action="store_true", help="só procura e escreve o relatório, não guarda nada")
    ap.add_argument("--seguir-artistas", action="store_true", help="segue também os artistas das linhas sem álbum")
    ap.add_argument("--relatorio", default="relatorio_spotify.txt", help="onde escrever o relatório")
    a = ap.parse_args()
    if not a.client_id:
        sys.exit("Falta o Client ID (--client-id ou SPOTIFY_CLIENT_ID).")

    token = login(a.client_id)
    with open(a.csv, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    albuns, artistas, nao = {}, {}, []
    for l in linhas:
        art, alb = l["artista"].strip(), (l.get("album") or "").strip()
        if alb:
            it = procurar(token, art, alb)
            if it:
                albuns[it["id"]] = f'{art} - {alb}  ->  {it["name"]}'
            else:
                nao.append(f"{art} - {alb}")
        elif a.seguir_artistas:
            it = procurar_artista(token, art)
            if it:
                artistas[it["id"]] = art
            else:
                nao.append(f"{art} (artista)")
        print(f'\r{len(albuns)} álbuns, {len(artistas)} artistas, {len(nao)} não encontrados', end="", flush=True)
    print()

    if not a.teste:
        guardar(token, "album", list(albuns))
        if artistas:
            guardar(token, "artist", list(artistas))
    with open(a.relatorio, "w", encoding="utf-8") as f:
        f.write("ENCONTRADOS\n" + "\n".join(albuns.values()) + "\n\nNÃO ENCONTRADOS\n" + "\n".join(nao) + "\n")
    print(("Teste: nada foi guardado. " if a.teste else "Guardado. ") + f"Relatório em {a.relatorio}")


if __name__ == "__main__":
    main()
