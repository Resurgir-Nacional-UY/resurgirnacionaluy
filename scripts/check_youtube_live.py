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
RECENT_HORAS = 6  # cuanto tiempo queda el aviso "directo finalizado" (el banner usa el mismo valor)


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


def read_prev():
    try:
        return json.loads(rd(OUT))
    except Exception:
        return {}


def api_get(endpoint, params):
    url = "https://www.googleapis.com/youtube/v3/%s?%s" % (endpoint, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_iso(ts):
    import datetime
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def main():
    if manual_override():
        write_if_changed({"live": True, "url": CHANNEL_LIVE_URL,
                           "title": "Transmisión en vivo"})
        return 0

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: falta la variable de entorno YOUTUBE_API_KEY (secreto del environment 'publicar')")
        return 0

    try:
        data = api_get("search", {"part": "snippet", "channelId": CHANNEL_ID, "eventType": "live",
                                  "type": "video", "maxResults": "1", "key": api_key})
    except Exception as e:
        print("WARNING: no se pudo consultar la YouTube Data API:", e)
        return 0

    prev = read_prev()
    items = data.get("items") or []
    video_id, title = "", ""
    if items:
        video_id = items[0].get("id", {}).get("videoId", "")
        title = items[0].get("snippet", {}).get("title", "")
    elif prev.get("videoId"):
        # La busqueda ya no lo devuelve: se sigue el ultimo video conocido para
        # saber cuando termino y mantener el aviso de "directo finalizado".
        video_id, title = prev["videoId"], prev.get("title", "")

    if not video_id:
        write_if_changed({"live": False})
        return 0

    # search.list sigue devolviendo una transmision ya terminada durante horas
    # (su indice se actualiza con retraso). videos.list si refleja el estado real.
    try:
        vdata = api_get("videos", {"part": "snippet,liveStreamingDetails", "id": video_id, "key": api_key})
    except Exception as e:
        print("WARNING: no se pudo confirmar el estado del video (se deja como estaba):", e)
        return 0
    vitems = vdata.get("items") or []
    v = vitems[0] if vitems else {}
    details = v.get("liveStreamingDetails", {})
    title = v.get("snippet", {}).get("title", title)
    url = "https://www.youtube.com/watch?v=" + video_id

    if v.get("snippet", {}).get("liveBroadcastContent") == "live" and not details.get("actualEndTime"):
        write_if_changed({"live": True, "videoId": video_id, "url": url, "title": title})
        return 0

    # Ya no esta en vivo: el aviso queda unas horas como "directo finalizado"
    # (el banner tambien lo oculta solo al pasar RECENT_HORAS, aunque este JSON no cambie).
    ended = details.get("actualEndTime")
    if ended:
        import datetime
        age = datetime.datetime.now(datetime.timezone.utc) - parse_iso(ended)
        if age < datetime.timedelta(hours=RECENT_HORAS):
            write_if_changed({"live": False, "videoId": video_id, "url": url,
                              "title": title, "endedAt": ended})
            return 0
    print("%s ya no esta en vivo y paso la ventana de %d h" % (video_id, RECENT_HORAS))
    write_if_changed({"live": False})
    return 0


if __name__ == "__main__":
    sys.exit(main())
