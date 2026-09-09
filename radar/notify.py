"""Salidas: Telegram (aviso push con botones) y Notion (seguimiento)."""
from __future__ import annotations

import html
import logging
import os

import requests

log = logging.getLogger(__name__)
TIMEOUT = 25
NOTION_VERSION = "2022-06-28"
API = "https://api.telegram.org/bot{token}/{metodo}"


def _tg(metodo: str, **payload):
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return None
    r = requests.post(API.format(token=token, metodo=metodo), json=payload, timeout=TIMEOUT)
    if not r.ok:
        log.error("Telegram %s: %s", metodo, r.text[:300])
    return r


# --------------------------------------------------------------------------- #
# Telegram
# --------------------------------------------------------------------------- #
def _teclado(job: dict) -> dict:
    """Botones de la oferta. callback_data va limitado a 64 bytes."""
    fila = [
        {"text": "✅ Me apunto", "callback_data": f"ok:{job['uid']}"},
        {"text": "🗑 Descartar", "callback_data": f"no:{job['uid']}"},
    ]
    enlaces = [{"text": "🔗 Ver oferta", "url": job["url"]}]
    if job.get("notion_page"):
        pagina = job["notion_page"].replace("-", "")
        enlaces.append({"text": "📋 Notion", "url": f"https://www.notion.so/{pagina}"})
    return {"inline_keyboard": [fila, enlaces]}


def telegram(jobs: list[dict]) -> int:
    """Un mensaje por oferta, para que cada una tenga sus propios botones."""
    if not (os.getenv("TELEGRAM_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")):
        log.warning("Telegram sin configurar, salto el aviso")
        return 0

    chat = os.getenv("TELEGRAM_CHAT_ID")
    enviados = 0
    if len(jobs) > 1:
        _tg("sendMessage", chat_id=chat,
            text=f"<b>Radar Odoo</b> · {len(jobs)} ofertas nuevas", parse_mode="HTML")

    for j in jobs:
        texto = (
            f"<b>{html.escape(j['title'][:100])}</b>\n"
            f"{html.escape(j.get('company') or '?')} · {html.escape(j.get('location') or '')}\n"
            f"Encaje: <b>{j.get('score', 0)}</b> · <code>{j.get('source','')}</code>"
        )
        r = _tg("sendMessage", chat_id=chat, text=texto, parse_mode="HTML",
                disable_web_page_preview=True, reply_markup=_teclado(j))
        if r is not None and r.ok:
            enviados += 1
    return enviados


# --------------------------------------------------------------------------- #
# Notion
# --------------------------------------------------------------------------- #
def _cabeceras() -> dict | None:
    token = os.getenv("NOTION_TOKEN")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"}


def notion(jobs: list[dict]) -> dict[str, str]:
    """Crea una ficha por oferta. Devuelve {uid: page_id} para poder editarlas."""
    cab = _cabeceras()
    db = os.getenv("NOTION_DB_ID")
    if not (cab and db):
        log.warning("Notion sin configurar, salto el volcado")
        return {}

    creadas: dict[str, str] = {}
    for j in jobs:
        props = {
            "Puesto": {"title": [{"text": {"content": j["title"][:180]}}]},
            "Empresa": {"rich_text": [{"text": {"content": (j.get("company") or "")[:120]}}]},
            "Ubicación": {"rich_text": [{"text": {"content": (j.get("location") or "")[:120]}}]},
            "Enlace": {"url": j.get("url")},
            "Fuente": {"select": {"name": j.get("source", "?")}},
            "Encaje": {"number": j.get("score", 0)},
            "Estado": {"select": {"name": "Nueva"}},
        }
        r = requests.post("https://api.notion.com/v1/pages", headers=cab,
                          json={"parent": {"database_id": db}, "properties": props},
                          timeout=TIMEOUT)
        if r.ok:
            creadas[j["uid"]] = r.json()["id"]
        else:
            log.error("Notion %s: %s", j["title"][:40], r.text[:200])
    return creadas


def notion_conocidas() -> dict[str, str]:
    """Devuelve {enlace: page_id} de todo lo que ya esta en la tabla.

    El historial local vive en la cache de GitHub Actions, que se puede perder.
    Notion no. Consultarla antes de avisar evita el peor fallo posible: soltar
    una tanda entera de ofertas repetidas porque se borro la cache.
    """
    cab = _cabeceras()
    db = os.getenv("NOTION_DB_ID")
    if not (cab and db):
        return {}

    conocidas: dict[str, str] = {}
    cursor = None
    while True:
        payload: dict = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(f"https://api.notion.com/v1/databases/{db}/query",
                          headers=cab, json=payload, timeout=TIMEOUT)
        if not r.ok:
            log.error("Notion consulta: %s", r.text[:200])
            return conocidas
        data = r.json()
        for pagina in data["results"]:
            enlace = pagina["properties"].get("Enlace", {}).get("url")
            if enlace:
                conocidas[enlace] = pagina["id"]
        if not data.get("has_more"):
            return conocidas
        cursor = data["next_cursor"]


def notion_estado(page_id: str, estado: str) -> bool:
    """Cambia el Estado de una ficha ya creada."""
    cab = _cabeceras()
    if not (cab and page_id):
        return False
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=cab,
                       json={"properties": {"Estado": {"select": {"name": estado}}}},
                       timeout=TIMEOUT)
    if not r.ok:
        log.error("Notion estado: %s", r.text[:200])
    return r.ok
