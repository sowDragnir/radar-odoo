"""Salidas: Telegram (aviso push) y Notion (seguimiento de candidaturas)."""
from __future__ import annotations

import html
import logging
import os

import requests

log = logging.getLogger(__name__)
TIMEOUT = 25
NOTION_VERSION = "2022-06-28"


# --------------------------------------------------------------------------- #
# Telegram
# --------------------------------------------------------------------------- #
def telegram(jobs: list[dict]) -> bool:
    token = os.getenv("TELEGRAM_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        log.warning("Telegram sin configurar, salto el aviso")
        return False
    if not jobs:
        return True

    lineas = [f"<b>Radar Odoo</b> — {len(jobs)} oferta(s) nueva(s)\n"]
    for j in jobs[:15]:
        titulo = html.escape(j["title"][:90])
        empresa = html.escape(j.get("company") or "?")
        sitio = html.escape(j.get("location") or "")
        lineas.append(
            f'\n<b>{titulo}</b>\n{empresa} · {sitio} · <i>{j["score"]} pts</i>\n'
            f'<a href="{j["url"]}">Ver oferta</a> · <code>{j["source"]}</code>'
        )
    if len(jobs) > 15:
        lineas.append(f"\n\n… y {len(jobs) - 15} más en Notion.")

    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": "".join(lineas), "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=TIMEOUT,
    )
    if not r.ok:
        log.error("Telegram: %s", r.text[:300])
    return r.ok


# --------------------------------------------------------------------------- #
# Notion
# --------------------------------------------------------------------------- #
def notion(jobs: list[dict]) -> int:
    token = os.getenv("NOTION_TOKEN")
    db = os.getenv("NOTION_DB_ID")
    if not (token and db):
        log.warning("Notion sin configurar, salto el volcado")
        return 0

    cabeceras = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    creadas = 0
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
        r = requests.post(
            "https://api.notion.com/v1/pages", headers=cabeceras,
            json={"parent": {"database_id": db}, "properties": props}, timeout=TIMEOUT,
        )
        if r.ok:
            creadas += 1
        else:
            log.error("Notion %s: %s", j["title"][:40], r.text[:200])
    return creadas
