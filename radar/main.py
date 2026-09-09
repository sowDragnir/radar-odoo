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

from . import config, gmail, match, notify, sources, store

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

    # Segunda red de seguridad: si la cache de Actions se perdio, la base local
    # viene vacia y todo parece nuevo. Notion recuerda lo que ya se aviso.
    if nuevas:
        conocidas = notify.notion_conocidas()
        if conocidas:
            repetidas = [j for j in nuevas if j["url"] in conocidas]
            for job in repetidas:
                store.guardar_notion_page(conn, job["uid"], conocidas[job["url"]])
            if repetidas:
                log.info("Ya estaban en Notion, no aviso de %d", len(repetidas))
                store.mark_notified(conn, repetidas)
                nuevas = [j for j in nuevas if j["url"] not in conocidas]
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
        # Notion primero: el aviso de Telegram lleva un boton a la ficha, y los
        # botones de estado necesitan saber que pagina tienen que actualizar.
        paginas = notify.notion(nuevas)
        for job in nuevas:
            page_id = paginas.get(job["uid"])
            if page_id:
                job["notion_page"] = page_id
                store.guardar_notion_page(conn, job["uid"], page_id)
        log.info("Notion: %d fichas creadas", len(paginas))

        log.info("Telegram: %d avisos enviados", notify.telegram(nuevas))

        # Borrador en Gmail para las que traen contacto: queda en Borradores,
        # con el CV adjunto, listo para revisar y enviar a mano.
        creados = gmail.borradores(nuevas)
        if creados:
            log.info("Gmail: %d borradores en la carpeta Borradores", creados)
        store.mark_notified(conn, nuevas)
    else:
        log.info("Sin novedades, no molesto")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
