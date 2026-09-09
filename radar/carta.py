"""Compone el borrador de correo que acompana a cada oferta con contacto.

No pretende sustituir a una carta escrita a mano: deja el esqueleto hecho con
los datos del puesto ya rellenados, para no partir de una hoja en blanco desde
el movil. Lo que de verdad convence -por que esa empresa y no otra- se anade
antes de enviar.

Los datos del perfil salen del CV (Desktop\\moi\\cv-src\\content.py).
"""
from __future__ import annotations

FIRMA = """Bassirou Sow
642 544 761 · neybassj@gmail.com
linkedin.com/in/bassirou-sow"""

BAZAS = [
    "Módulos a medida sobre Odoo v15–v19: MRP y fabricación, inventario, ventas.",
    "Trazabilidad FEFO, códigos de barras y GS1 DataMatrix en entornos de almacén.",
    "PostgreSQL, incluida optimización de consultas cuando el volumen aprieta.",
    "Despliegue y administración: Docker Compose, Linux, Git.",
    "Integraciones: APIs REST, procesos ETL, n8n y Selenium.",
]

# Ciudades desde las que el puesto es viable sin mudarse.
CERCA = ("barcelona", "terrassa", "sabadell", "vallès", "valles", "cataluña",
         "catalunya", "remoto", "remote", "españa", "spain")


def _pregunta_ubicacion(job: dict) -> str:
    """Si la empresa esta lejos, preguntarlo de entrada ahorra tiempo a los dos."""
    sitio = f"{job.get('location', '')}".lower()
    if not sitio or any(c in sitio for c in CERCA):
        return ""
    return (f"\n\nUna cuestión práctica antes de nada: estoy en Terrassa "
            f"(Barcelona). ¿Contempláis la posición en remoto, o necesitáis "
            f"presencia en {job.get('location')}? Si es lo segundo os lo digo "
            f"ya, para no haceros perder tiempo.")


def asunto(job: dict) -> str:
    puesto = (job.get("title") or "").strip()
    if job.get("source") == "partner-watch":
        return "Desarrollador Odoo (4 años, v15–v19) — candidatura espontánea"
    return f"{puesto[:70]} — Bassirou Sow (4 años en Odoo)"


def cuerpo(job: dict) -> str:
    empresa = job.get("company") or "vosotros"
    puesto = (job.get("title") or "").strip()

    if job.get("source") == "partner-watch":
        # No hay oferta concreta: es una candidatura espontánea.
        entrada = (f"Os escribo porque sigo el trabajo de {empresa} en el "
                   f"ecosistema Odoo y me gustaría formar parte de un equipo "
                   f"que trabaja así.")
    else:
        entrada = (f"Os escribo por vuestra oferta de {puesto}. Encaja con lo "
                   f"que llevo haciendo los últimos 4 años, así que prefiero "
                   f"escribiros directamente antes que dejar la candidatura "
                   f"en un portal.")

    bazas = "\n".join(f"· {b}" for b in BAZAS)

    return (
        f"Hola,\n\n{entrada}\n\n"
        f"Soy desarrollador Python especializado en Odoo, con 4 años entregando "
        f"ERP en producción para clientes reales, tanto On-Premise como en Odoo "
        f"Online (SaaS). En concreto:\n\n{bazas}"
        f"{_pregunta_ubicacion(job)}\n\n"
        f"Os dejo el CV adjunto. Quedo a vuestra disposición.\n\n"
        f"Un saludo,\n{FIRMA}"
    )


def bloques_notion(job: dict) -> list[dict]:
    """El borrador como bloques de Notion, para pegarlo dentro de la ficha."""
    def parrafo(texto: str) -> dict:
        return {"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text",
                                             "text": {"content": texto[:1900]}}]}}

    bloques = [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text",
                                      "text": {"content": "Borrador de correo"}}]}},
        {"object": "block", "type": "callout",
         "callout": {"icon": {"emoji": "✏️"},
                     "rich_text": [{"type": "text", "text": {"content":
                         "Esqueleto automático. Añade una frase concreta sobre "
                         "esta empresa antes de enviarlo, y adjunta el CV."}}]}},
        parrafo(f"Para: {job.get('email', '')}"),
        parrafo(f"Asunto: {asunto(job)}"),
    ]
    for trozo in cuerpo(job).split("\n\n"):
        bloques.append(parrafo(trozo))
    return bloques
