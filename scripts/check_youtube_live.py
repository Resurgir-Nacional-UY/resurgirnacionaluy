#!/usr/bin/env python3
"""Consulta la YouTube Data API y publica el estado "en vivo" del canal.

Escribe live-status.json en la raiz del repo. El banner embebido en el
<header> (ver tools/src/index.html) lo lee con fetch() en cada carga de
pagina y muestra/oculta el aviso segun el campo "live".

Antes de consultar la API mira content/pages/live.yml (el interruptor manual
del CMS, colección Páginas > "🔴 Transmisión en vivo"): si esta activado,
publica "en vivo" al toque usando el link /live del canal -- sin esperar la
consulta a la API, que puede tardar hasta 20 minutos (el intervalo del
cron) y ademas puede tardar un rato en detectar una transmision recien
arrancada. Si esta desactivado, corre la consulta real de siempre.

Nunca falla el job de GitHub Actions a proposito: un hipo de la API (cuota,
red) o un secreto mal configurado no deben mandar un correo de fallo cada
vez que corre el cron (cada 20 minutos). Si la consulta falla, se deja
live-status.json como estaba -- mejor un aviso desactualizado unos minutos
que apagar uno real por un error pasajero.

Variables de entorno:
    YOUTUBE_API_KEY  -- obligatoria, cargada como secreto en GitHub
                        (environment "publicar", igual que PUSH_TOKEN).

Correr desde la raiz del repo:  python scripts/check_youtube_live.py
"""
import io, json, os, sys, urllib.parse, urllib.request
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "live-status.json")
MANUAL = os.path.join(ROOT, "content", "pages", "live.yml")
CHANNEL_ID = "UCHZVDhnLmw73slFZadO7oFw"  # @ResurgirNacional
CHANNEL_LIVE_URL = "https://www.youtube.com/@ResurgirNacional/live"


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def manual_override():
    """True si el interruptor manual del CMS (Páginas > Transmisión en vivo)
    esta activado."""
    if not os.path.exists(MANUAL):
        return False
    try:
        data = yaml.safe_load(rd(MANUAL))
    except Exception:
        return False
    return bool(isinstance(data, dict) and data.get("live_now"))


def write_if_changed(new):
    old = None
    if os.path.exists(OUT):
        try:
            old = json.loads(rd(OUT))
        except Exception:
            old = None
    if new != old:
        wr(OUT, json.dumps(new, ensure_ascii=False) + "\n")
        print("live-status.json actualizado:", new)
    else:
        print("Sin cambios (en vivo: %s)" % new["live"])


def main():
    if manual_override():
        write_if_changed({"live": True, "url": CHANNEL_LIVE_URL,
                           "title": "Transmisión en vivo"})
        return 0

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: falta la variable de entorno YOUTUBE_API_KEY (secreto del environment 'publicar')")
        return 0

    qs = urllib.parse.urlencode({
        "part": "snippet",
        "channelId": CHANNEL_ID,
        "eventType": "live",
        "type": "video",
        "maxResults": "1",
        "key": api_key,
    })
    url = "https://www.googleapis.com/youtube/v3/search?" + qs
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("WARNING: no se pudo consultar la YouTube Data API:", e)
        return 0

    items = data.get("items") or []
    if items:
        item = items[0]
        video_id = item.get("id", {}).get("videoId", "")
        title = item.get("snippet", {}).get("title", "")
        new = {"live": True, "videoId": video_id,
               "url": "https://www.youtube.com/watch?v=" + video_id,
               "title": title}
    else:
        new = {"live": False}

    write_if_changed(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
