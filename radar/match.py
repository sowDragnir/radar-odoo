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


CUERPO_MAX = 45  # techo de lo que puede aportar la descripcion


def score(job: dict) -> int:
    text = job["text"]
    if not _has(text, config.KEYWORDS):
        return 0

    titulo = job.get("title", "").lower()
    if _has(titulo, config.TITULO_VETO) and not _has(titulo, config.TITULO_SALVA):
        return 0

    # El titulo cuenta entero; la descripcion, a cuarto de peso y con techo.
    # Casi cualquier oferta de backend nombra Python, Docker y Postgres en su
    # lista de deseos: sin este freno, todas parecian encajar.
    puntos = sum(w for k, w in config.BOOST.items() if k in titulo)
    cuerpo = sum(w for k, w in config.BOOST.items() if k in text and k not in titulo)
    puntos += min(cuerpo // 4, CUERPO_MAX)

    puntos -= sum(w for k, w in config.PENALIZA.items() if k in text)

    if "odoo" in titulo:
        puntos += 30
    elif any(k in titulo for k in ("python", "fastapi", "django", "flask", "backend")):
        puntos += 15
    if job.get("source", "").startswith("partner"):
        puntos += 25  # un partner de Odoo moviendo ficha es la senal mas fuerte
    return puntos


def keep(job: dict) -> bool:
    job["score"] = score(job)
    return job["score"] >= config.MIN_SCORE and location_ok(job)


def filtrar(jobs: list[dict]) -> list[dict]:
    out = [j for j in jobs if keep(j)]
    out.sort(key=lambda j: j["score"], reverse=True)
    return out
