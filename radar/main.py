"""Punto de entrada del radar.

    python -m radar.main            # ciclo completo
    python -m radar.main --dry-run  # no notifica, solo muestra
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from . import config, match, notify, sources, store

RAIZ = Path(__file__).resolve().parent.parent


def cargar_env() -> None:
    """Lee .env si existe. En GitHub Actions las variables ya vienen del entorno."""
    env = RAIZ / ".env"
    if not env.exists():
        return
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip())


def cargar_partners() -> list[dict]:
    fichero = RAIZ / "partners.json"
    if not fichero.exists():
        return []
    return json.loads(fichero.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Radar de ofertas Odoo/Python")
    parser.add_argument("--dry-run", action="store_true", help="no envia avisos")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    log = logging.getLogger("radar")
    cargar_env()

    conn = store.connect()

    brutas = sources.collect()
    partners = cargar_partners()
    if partners:
        try:
            brutas += sources.partner_pages(partners, conn)
        except Exception as exc:
            log.warning("partner_pages FALLO: %s", exc)

    log.info("Recogidas %d ofertas en bruto", len(brutas))

    candidatas = match.filtrar(brutas)
    log.info("Pasan el filtro %d", len(candidatas))

    nuevas = store.new_jobs(conn, candidatas)
    log.info("Nuevas (no vistas antes) %d", len(nuevas))
    if len(nuevas) > config.MAX_AVISOS:
        log.info("Recorto a las %d mejores", config.MAX_AVISOS)
        nuevas = nuevas[:config.MAX_AVISOS]

    for j in nuevas[:20]:
        log.info("  %3d pts | %-45s | %-22s | %s",
                 j["score"], j["title"][:45], (j.get("company") or "")[:22], j["source"])

    if args.dry_run:
        log.info("--dry-run: no se envia nada")
        return 0

    if nuevas:
        if notify.telegram(nuevas):
            log.info("Telegram enviado")
        creadas = notify.notion(nuevas)
        if creadas:
            log.info("Notion: %d fichas creadas", creadas)
        store.mark_notified(conn, nuevas)
    else:
        log.info("Sin novedades, no molesto")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
