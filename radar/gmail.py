"""Deja borradores en Gmail, con el CV adjunto, via IMAP.

Por que IMAP y no la API de Gmail: la API exige un proyecto en Google Cloud con
OAuth, y en modo "Testing" el refresh token **caduca a los 7 dias**, asi que la
automatizacion se romperia sola cada semana sin avisar. Con una contrasena de
aplicacion basta con un secreto y no caduca.

El CV se descarga del portfolio publico del propio usuario en vez de vivir en
este repositorio, que es publico y no debe contener datos de contacto.
"""
from __future__ import annotations

import imaplib
import logging
import os
import time
from email.message import EmailMessage
from email.utils import formatdate

import requests

from . import carta

log = logging.getLogger(__name__)

SERVIDOR = "imap.gmail.com"
CARPETAS = ("[Gmail]/Drafts", "[Gmail]/Borradores", "Drafts", "Borradores")
CV_URL = os.getenv("CV_URL",
                   "https://sowsociety.netlify.app/assets/cv/cv-bassirou-sow-es.pdf")
CV_NOMBRE = "CV_Bassirou_Sow.pdf"
TIMEOUT = 30

_cv_cache: bytes | None = None


def _cv() -> bytes | None:
    """Descarga el CV una sola vez por ejecucion."""
    global _cv_cache
    if _cv_cache is None:
        try:
            r = requests.get(CV_URL, timeout=TIMEOUT)
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                log.error("La URL del CV no devuelve un PDF")
                return None
            _cv_cache = r.content
            log.info("CV descargado (%d KB)", len(_cv_cache) // 1024)
        except requests.RequestException as exc:
            log.error("No se pudo descargar el CV: %s", exc)
            return None
    return _cv_cache


def _mensaje(job: dict, remitente: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = remitente
    msg["To"] = job["email"]
    msg["Subject"] = carta.asunto(job)
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(carta.cuerpo(job))

    pdf = _cv()
    if pdf:
        msg.add_attachment(pdf, maintype="application", subtype="pdf",
                           filename=CV_NOMBRE)
    return msg


def _carpeta_borradores(imap: imaplib.IMAP4_SSL) -> str | None:
    """Gmail nombra la carpeta segun el idioma de la cuenta."""
    ok, buzones = imap.list()
    if ok != "OK":
        return None
    nombres = [b.decode("utf-8", "replace") for b in buzones]
    for candidata in CARPETAS:
        if any(f'"{candidata}"' in n or n.endswith(candidata) for n in nombres):
            return candidata
    # Ultimo recurso: la carpeta marcada con el atributo \Drafts
    for linea in nombres:
        if "\\Drafts" in linea:
            return linea.split('"')[-2] if '"' in linea else None
    return None


def borradores(jobs: list[dict]) -> int:
    """Crea un borrador por oferta con contacto. Devuelve cuantos se crearon."""
    usuario = os.getenv("GMAIL_USER")
    clave = os.getenv("GMAIL_APP_PASSWORD")
    if not (usuario and clave):
        log.info("Gmail sin configurar, no creo borradores")
        return 0

    con_contacto = [j for j in jobs if j.get("email")]
    if not con_contacto:
        return 0

    try:
        imap = imaplib.IMAP4_SSL(SERVIDOR, timeout=TIMEOUT)
        imap.login(usuario, clave.replace(" ", ""))
    except (imaplib.IMAP4.error, OSError) as exc:
        log.error("Gmail IMAP: %s", exc)
        return 0

    try:
        carpeta = _carpeta_borradores(imap)
        if not carpeta:
            log.error("No encuentro la carpeta de borradores")
            return 0

        creados = 0
        for job in con_contacto:
            mensaje = _mensaje(job, usuario)
            ok, _ = imap.append(f'"{carpeta}"', "\\Draft",
                                imaplib.Time2Internaldate(time.time()),
                                mensaje.as_bytes())
            if ok == "OK":
                creados += 1
                log.info("Borrador: %s -> %s", job["title"][:40], job["email"])
            else:
                log.error("No se pudo crear el borrador de %s", job["title"][:40])
        return creados
    finally:
        try:
            imap.logout()
        except Exception:
            pass
