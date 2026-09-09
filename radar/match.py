"""Filtro y puntuacion: decide que oferta merece un aviso."""
from __future__ import annotations

from . import config


def _has(text: str, needles) -> bool:
    return any(n in text for n in needles)


def location_ok(job: dict) -> bool:
    """Barcelona en cualquier modalidad, Madrid solo remoto, o remoto general."""
    text = f"{job.get('location','')} {job.get('text','')}".lower()
    if _has(text, config.BLOCK):
        return False
    remote = _has(text, config.REMOTE_HINTS)
    if _has(text, config.BARCELONA):
        return True
    if _has(text, config.MADRID):
        return remote
    if remote:
        # Remoto vale si no excluye Espana/Europa explicitamente.
        return not _has(text, ["usa only", "americas only", "apac only"])
    return False


def score(job: dict) -> int:
    text = job["text"]
    if not _has(text, config.KEYWORDS):
        return 0
    points = sum(w for k, w in config.BOOST.items() if k in text)
    if "odoo" in job.get("title", "").lower():
        points += 30  # el titulo pesa mas que el cuerpo
    if job.get("source", "").startswith("partner"):
        points += 25  # un partner de Odoo moviendo ficha es la senal mas fuerte
    return points


def keep(job: dict) -> bool:
    job["score"] = score(job)
    return job["score"] >= config.MIN_SCORE and location_ok(job)


def filtrar(jobs: list[dict]) -> list[dict]:
    out = [j for j in jobs if keep(j)]
    out.sort(key=lambda j: j["score"], reverse=True)
    return out
