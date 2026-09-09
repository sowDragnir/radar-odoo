"""Fuentes de ofertas. Cada funcion devuelve una lista de dicts homogeneos.

Solo se usan APIs publicas y documentadas o feeds RSS. Nada de scraping de
portales que lo prohiben: LinkedIn queda fuera a proposito.
"""
from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import datetime, timezone

import requests

log = logging.getLogger(__name__)
UA = {"User-Agent": "radar-odoo/1.0"}
TIMEOUT = 25


def _get(url: str, **kw):
    r = requests.get(url, headers=UA, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _strip(text: str) -> str:
    """Quita etiquetas HTML y deja texto plano."""
    return re.sub(r"<[^>]+>", " ", html.unescape(text or ""))


def _estable(texto: str) -> str:
    """Quita lo que cambia solo en cada carga y dispararia falsas alarmas.

    Muchas webs meten nonces, ids de sesion, contadores de cookies o la fecha
    en el HTML. Sin esto, el vigilante avisaria a diario de un cambio que no
    existe. Se queda solo con palabras de letras, que es donde vive una oferta.
    """
    # Ojo: hay que descartar el token entero, no extraerle las letras. Sacar
    # las letras de un nonce como "d4a2cb" produce "dacb", una palabra falsa
    # que cambia en cada carga y dispara la alarma igualmente.
    palabras = [t for t in texto.split() if re.fullmatch(r"[a-zñáéíóúü]{3,}", t)]
    return " ".join(palabras)


def _job(title, company, location, url, source, posted=None, text="",
         email=None) -> dict:
    return {
        "email": email,
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "").strip(),
        "url": url,
        "source": source,
        "posted": posted,
        "text": f"{title} {company} {location} {text}".lower(),
    }


# --------------------------------------------------------------------------- #
# Bolsas remotas con API abierta
# --------------------------------------------------------------------------- #
def remoteok() -> list[dict]:
    data = _get("https://remoteok.com/api").json()
    out = []
    for it in data:
        if not isinstance(it, dict) or "position" not in it:
            continue  # el primer elemento del feed es el aviso legal
        out.append(_job(
            it.get("position"), it.get("company"), it.get("location") or "Remote",
            it.get("url"), "remoteok", it.get("date"),
            " ".join(it.get("tags") or []) + " " + _strip(it.get("description", ""))[:2000],
        ))
    return out


def remotive() -> list[dict]:
    out = []
    for term in ("odoo", "python"):
        data = _get(f"https://remotive.com/api/remote-jobs?search={term}&limit=100").json()
        for it in data.get("jobs", []):
            out.append(_job(
                it.get("title"), it.get("company_name"),
                it.get("candidate_required_location") or "Remote",
                it.get("url"), "remotive", it.get("publication_date"),
                _strip(it.get("description", ""))[:2000],
            ))
    return out


def arbeitnow() -> list[dict]:
    out = []
    for page in (1, 2, 3):
        data = _get(f"https://www.arbeitnow.com/api/job-board-api?page={page}").json()
        for it in data.get("data", []):
            created = it.get("created_at") or 0
            out.append(_job(
                it.get("title"), it.get("company_name"),
                it.get("location") or ("Remote" if it.get("remote") else ""),
                it.get("url"), "arbeitnow",
                datetime.fromtimestamp(created, timezone.utc).isoformat(),
                " ".join(it.get("tags") or []) + " " + _strip(it.get("description", ""))[:2000],
            ))
    return out


def jobicy() -> list[dict]:
    out = []
    for tag in ("python", "erp"):
        data = _get(f"https://jobicy.com/api/v2/remote-jobs?count=50&tag={tag}").json()
        for it in data.get("jobs", []):
            out.append(_job(
                it.get("jobTitle"), it.get("companyName"), it.get("jobGeo") or "Remote",
                it.get("url"), "jobicy", it.get("pubDate"),
                _strip(it.get("jobExcerpt", "")),
            ))
    return out


def weworkremotely() -> list[dict]:
    xml = _get("https://weworkremotely.com/categories/remote-programming-jobs.rss").text
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def tag(name, blob=item):
            m = re.search(rf"<{name}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", blob, re.S)
            return html.unescape(m.group(1)).strip() if m else ""

        title = tag("title")
        company, _, role = title.partition(":")
        out.append(_job(
            role or title, company, tag("region") or "Remote",
            tag("link"), "weworkremotely", tag("pubDate"), _strip(tag("description"))[:2000],
        ))
    return out


# --------------------------------------------------------------------------- #
# Odoo S.A. tiene oficina en Barcelona. country_id=67 es Espana.
# --------------------------------------------------------------------------- #
def odoo_sa() -> list[dict]:
    out = []
    try:
        page = _get("https://www.odoo.com/jobs?country_id=67").text
    except requests.RequestException as exc:
        log.warning("odoo_sa: %s", exc)
        return out
    seen = set()
    for href in re.findall(r'href="(/jobs/[a-z0-9-]+-\d+)"', page):
        if href in seen:
            continue
        seen.add(href)
        # El titulo no esta en el texto del enlace: lo saco del slug, que es
        # estable aunque rediseñen la pagina.
        slug = href.rsplit("/", 1)[-1].rsplit("-", 1)[0]
        title = slug.replace("-", " ").title()
        out.append(_job(title, "Odoo S.A.", "Barcelona / Remote",
                        "https://www.odoo.com" + href, "odoo.com", None, title))
    return out


# --------------------------------------------------------------------------- #
# Hacker News "Who is hiring?" del mes en curso
# --------------------------------------------------------------------------- #
def hackernews() -> list[dict]:
    hits = _get("https://hn.algolia.com/api/v1/search_by_date"
                "?tags=story,author_whoishiring&hitsPerPage=5").json()["hits"]
    story = next((h for h in hits if "who is hiring" in h["title"].lower()), None)
    if not story:
        return []
    item = _get(f"https://hn.algolia.com/api/v1/items/{story['objectID']}").json()
    # HN es 90% EE.UU.: solo dejo pasar lo que menciona Europa/Espana o Odoo.
    europa = ("europe", "eu ", "emea", "spain", "españa", "barcelona", "madrid",
              "worldwide", "anywhere", "cet", "odoo")
    out = []
    for child in item.get("children", []):
        body = " ".join(_strip(child.get("text") or "").split())
        if not body:
            continue
        low = body.lower()
        if not any(k in low for k in europa):
            continue
        head = body.split("|")[0].strip()[:60]
        out.append(_job(
            " ".join(body.split()[:12]), head, "ver anuncio",
            f"https://news.ycombinator.com/item?id={child['id']}",
            "hackernews", None, body,
        ))
    return out


# --------------------------------------------------------------------------- #
# Partners de Odoo en Espana: vigilancia de su pagina de empleo
# --------------------------------------------------------------------------- #
def partner_pages(partners: list[dict], conn) -> list[dict]:
    """Vigila la pagina de empleo de cada partner de Odoo en Espana.

    Dos estrategias, porque no todos publican igual:

    1. Muchos partners montan su web con el propio modulo de RRHH de Odoo, que
       expone las vacantes como /jobs/<slug>-<id>. Ahi se leen una a una.
    2. El resto no tiene estructura fiable: se normaliza el texto, se guarda un
       hash y se avisa cuando cambia. No se rompe con los redisenos.
    """
    from .store import page_changed

    watched = ("odoo", "python", "desarrollador", "developer", "programador")
    out = []
    for p in partners:
        url = p.get("careers") or p.get("web")
        if not url:
            continue
        try:
            raw = _get(url).text
        except requests.RequestException as exc:
            log.warning("partner %s: %s", p.get("name"), exc)
            continue

        base = re.match(r"https?://[^/]+", url).group(0)
        vistos = set()
        for href in re.findall(r'href="(/jobs/[a-z0-9-]+-\d+)"', raw):
            if href in vistos:
                continue
            vistos.add(href)
            slug = href.rsplit("/", 1)[-1].rsplit("-", 1)[0]
            titulo = slug.replace("-", " ").title()
            out.append(_job(titulo, p.get("name"), p.get("city", "España"),
                            base + href, "partner-odoo", None, titulo,
                            email=(p.get("emails") or [None])[0]))
        if vistos:
            continue  # ya tengo las ofertas concretas, no hace falta el hash

        norm = " ".join(_strip(raw).lower().split())
        digest = hashlib.sha1(_estable(norm).encode("utf-8")).hexdigest()
        hits = [k for k in watched if k in norm]
        if page_changed(conn, url, p.get("name", url), digest) and hits:
            out.append(_job(
                f"Cambio en su pagina de empleo ({', '.join(hits[:3])})",
                p.get("name"), p.get("city", "España"), url,
                "partner-watch", None, norm[:1500],
                email=(p.get("emails") or [None])[0],
            ))
    return out


ALL = [remoteok, remotive, arbeitnow, jobicy, weworkremotely, odoo_sa, hackernews]


def collect() -> list[dict]:
    """Recorre todas las fuentes. Una fuente caida no tumba el radar."""
    jobs = []
    for fn in ALL:
        try:
            got = fn()
            log.info("%-16s %3d ofertas", fn.__name__, len(got))
            jobs += got
        except Exception as exc:
            log.warning("%-16s FALLO: %s", fn.__name__, exc)
    return jobs
