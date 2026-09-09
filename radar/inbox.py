"""Recoge las pulsaciones de los botones de Telegram y las lleva a Notion.

El radar corre una vez al dia, asi que cuando pulsas un boton no hay nadie
escuchando. Telegram guarda las pulsaciones en cola 24 h: este modulo las
vacia y actualiza la ficha correspondiente.

    python -m radar.inbox
"""
from __future__ import annotations

import logging
import os

import requests

from . import notify, store

log = logging.getLogger(__name__)
TIMEOUT = 30

ACCIONES = {
    "ok": ("Interesa", "✅ Apuntada"),
    "no": ("Descartada", "🗑 Descartada"),
}


# Errores esperados en modo diferido: el radar no esta escuchando cuando pulsas,
# asi que el "toast" de confirmacion casi siempre llega caducado. No es un fallo.
ESPERADOS = ("query is too old", "message is not modified",
             "query ID is invalid", "message to edit not found")


def _api(metodo: str, **payload):
    token = os.getenv("TELEGRAM_TOKEN")
    r = requests.post(f"https://api.telegram.org/bot{token}/{metodo}",
                      json=payload, timeout=TIMEOUT)
    if not r.ok:
        detalle = r.json().get("description", "") if r.headers.get(
            "content-type", "").startswith("application/json") else r.text
        nivel = log.debug if any(e in detalle for e in ESPERADOS) else log.error
        nivel("Telegram %s: %s", metodo, detalle[:160])
    return r


def procesar(conn) -> int:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        log.error("Falta TELEGRAM_TOKEN")
        return 0

    offset = store.ajuste(conn, "tg_offset")
    params = {"timeout": 0, "allowed_updates": ["callback_query"]}
    if offset:
        params["offset"] = int(offset) + 1

    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates",
                     params=params, timeout=TIMEOUT)
    r.raise_for_status()
    updates = r.json().get("result", [])
    log.info("%d pulsacion(es) en cola", len(updates))

    # Si pulsas varias veces la misma oferta, manda la ultima decision.
    ultimas: dict[str, dict] = {}
    for upd in updates:
        store.ajuste(conn, "tg_offset", str(upd["update_id"]))
        cb = upd.get("callback_query")
        if cb and cb.get("data"):
            ultimas[cb["data"].partition(":")[2]] = cb
    if len(updates) > len(ultimas):
        log.info("%d pulsaciones colapsadas en %d decisiones",
                 len(updates), len(ultimas))

    tratadas = 0
    for cb in ultimas.values():
        accion, _, uid = (cb.get("data") or "").partition(":")
        estado, etiqueta = ACCIONES.get(accion, (None, None))
        if not estado:
            continue

        job = store.buscar(conn, uid)
        if job is None:
            _api("answerCallbackQuery", callback_query_id=cb["id"],
                 text="No encuentro esa oferta en el historial")
            continue

        ok = notify.notion_estado(job["notion_page"], estado) if job["notion_page"] else False
        _api("answerCallbackQuery", callback_query_id=cb["id"],
             text=f"{etiqueta} en Notion" if ok else "Guardado, pero Notion no respondio")

        # Deja el mensaje marcado para que se vea de un vistazo en el movil.
        # Se reescribe la marca anterior en vez de acumularlas.
        mensaje = cb.get("message") or {}
        if mensaje.get("message_id"):
            cuerpo = (mensaje.get("text") or "")
            for _, marca in ACCIONES.values():
                cuerpo = cuerpo.replace(f"\n\n{marca}", "")
            _api("editMessageText",
                 chat_id=mensaje["chat"]["id"], message_id=mensaje["message_id"],
                 text=f"{cuerpo}\n\n{etiqueta}",
                 reply_markup={"inline_keyboard": [[
                     {"text": "🔗 Ver oferta", "url": job["url"]}]]})
        tratadas += 1
        log.info("%s -> %s", job["title"][:50], estado)

    return tratadas


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    from .main import cargar_env
    cargar_env()
    conn = store.connect()
    log.info("Actualizadas %d fichas", procesar(conn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
