#!/usr/bin/env python3
"""Consulta la YouTube Data API y publica el estado "en vivo" del canal.

Escribe live-status.json en la raiz del repo. El banner embebido en el
<header> de todas las paginas (ver tools/src/index.html) lo lee con fetch()
en cada carga y muestra/oculta el aviso segun el estado:

    {"live": true,  "videoId", "url", "title"}               -> "Estamos EN VIVO ahora"
    {"live": false, "videoId", "url", "title", "endedAt"}    -> "Directo finalizado" (hasta 6 h)
    {"live": false}                                          -> sin aviso

Interruptor manual (CMS: Páginas > "🔴 Transmisión en vivo", content/pages/live.yml)
----------------------------------------------------------------------------------
Al ACTIVARLO (pasa de apagado a encendido) se publica "en vivo" al toque y se
reemplaza lo que hubiera: tambien un aviso viejo de "directo finalizado". Si la
API ya ve la transmision nueva se usa su link y titulo; si no, el link /live del
canal (que siempre apunta a la transmision actual). Para "reiniciar" el aviso con
otro directo hay que desactivarlo y volver a activarlo.

Despues el estado real manda: cuando la API ve que la transmision que arranco
despues del interruptor termino, pasa a "directo finalizado". Si la API nunca la
vio, el aviso manual dura como maximo MANUAL_MAX_HORAS. El campo "manual" del
JSON recuerda que el interruptor ya se proceso (para no reiniciar el aviso en
cada consulta mientras siga encendido); se borra al apagarlo.

Nunca falla el job de GitHub Actions a proposito: un hipo de la API (cuota,
red) o un secreto mal configurado no deben mandar un correo de fallo cada vez
que corre el cron. Si la consulta falla, se deja live-status.json como estaba --
mejor un aviso desactualizado unos minutos que apagar uno real por un error pasajero.

Variables de entorno:
    YOUTUBE_API_KEY  -- obligatoria, cargada como secreto en GitHub
                        (environment "publicar", igual que PUSH_TOKEN).

Correr desde la raiz del repo:  python scripts/check_youtube_live.py
"""
import datetime, io, json, os, sys, urllib.parse, urllib.request
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "live-status.json")
MANUAL = os.path.join(ROOT, "content", "pages", "live.yml")
CHANNEL_ID = "UCHZVDhnLmw73slFZadO7oFw"  # @ResurgirNacional
CHANNEL_LIVE_URL = "https://www.youtube.com/@ResurgirNacional/live"
RECENT_HORAS = 6        # cuanto queda el aviso "directo finalizado" (el banner usa el mismo valor)
MANUAL_MAX_HORAS = 12   # tope del aviso manual si la API nunca llega a ver la transmision


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def manual_override():
    """True si el interruptor manual del CMS esta activado."""
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
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def horas_desde(ts):
    return (datetime.datetime.now(datetime.timezone.utc) - parse_iso(ts)).total_seconds() / 3600.0


def api_state(api_key, prev):
    """Estado real segun la API: ("keep", None, None) si la API fallo, o
    ("state", dict, ended_iso) con live / directo finalizado / sin aviso."""
    try:
        data = api_get("search", {"part": "snippet", "channelId": CHANNEL_ID, "eventType": "live",
                                  "type": "video", "maxResults": "1", "key": api_key})
    except Exception as e:
        print("WARNING: no se pudo consultar la YouTube Data API:", e)
        return "keep", None, None

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
        return "state", {"live": False}, None

    # search.list sigue devolviendo una transmision ya terminada durante horas
    # (su indice se actualiza con retraso). videos.list si refleja el estado real.
    try:
        vdata = api_get("videos", {"part": "snippet,liveStreamingDetails", "id": video_id, "key": api_key})
    except Exception as e:
        print("WARNING: no se pudo confirmar el estado del video (se deja como estaba):", e)
        return "keep", None, None
    vitems = vdata.get("items") or []
    v = vitems[0] if vitems else {}
    details = v.get("liveStreamingDetails", {})
    title = v.get("snippet", {}).get("title", title)
    url = "https://www.youtube.com/watch?v=" + video_id

    if v.get("snippet", {}).get("liveBroadcastContent") == "live" and not details.get("actualEndTime"):
        return "state", {"live": True, "videoId": video_id, "url": url, "title": title}, None

    ended = details.get("actualEndTime")
    if ended and horas_desde(ended) < RECENT_HORAS:
        return "state", {"live": False, "videoId": video_id, "url": url, "title": title,
                         "endedAt": ended}, ended
    print("%s ya no esta en vivo y paso la ventana de %d h" % (video_id, RECENT_HORAS))
    return "state", {"live": False}, ended


def main():
    toggle = manual_override()
    prev = read_prev()
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()

    # Interruptor recien activado: aviso "en vivo" al toque, reemplazando lo anterior.
    if toggle and not prev.get("manual"):
        new = None
        if api_key:
            status, found, _ = api_state(api_key, {})   # sin historia: solo lo que esta en vivo ahora
            if status == "state" and found.get("live"):
                new = found
        if new is None:
            new = {"live": True, "url": CHANNEL_LIVE_URL, "title": "Transmisión en vivo"}
        new["manual"] = True
        new["since"] = now_iso()
        write_if_changed(new)
        return 0

    if not api_key:
        print("ERROR: falta la variable de entorno YOUTUBE_API_KEY (secreto del environment 'publicar')")
        return 0

    status, new, ended = api_state(api_key, prev)
    if status == "keep":
        return 0

    if toggle:
        since = prev.get("since") or now_iso()
        if not new.get("live"):
            # El aviso manual se mantiene salvo que la API confirme que termino la
            # transmision que arranco despues del interruptor, o pase el tope de horas.
            termino_la_nueva = bool(ended) and parse_iso(ended) > parse_iso(since)
            if prev.get("live") and horas_desde(since) < MANUAL_MAX_HORAS and not termino_la_nueva:
                print("Interruptor manual vigente: se mantiene el aviso en vivo")
                return 0
        new["manual"] = True
        new["since"] = since

    write_if_changed(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
