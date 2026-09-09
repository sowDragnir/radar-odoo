"""Persistencia: una oferta vista no se vuelve a notificar nunca."""
import hashlib
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "radar.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    uid        TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    company    TEXT,
    location   TEXT,
    url        TEXT,
    source     TEXT,
    score      INTEGER,
    posted     TEXT,
    seen_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    notified   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS watch (
    url        TEXT PRIMARY KEY,
    name       TEXT,
    digest     TEXT,
    checked_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT
);
"""

# Columnas anadidas despues de la primera version. SQLite no tiene
# "ADD COLUMN IF NOT EXISTS", asi que se prueba y se ignora si ya existe.
EXTRA = [
    "ALTER TABLE jobs ADD COLUMN notion_page TEXT",
    "ALTER TABLE jobs ADD COLUMN email TEXT",
    "ALTER TABLE watch ADD COLUMN texto TEXT",
]


def uid(job: dict) -> str:
    """Identidad estable: misma oferta en dos fuentes = un solo aviso."""
    base = f"{job.get('company','')}|{job.get('title','')}".lower().strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def connect(path: Path = DB) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for sql in EXTRA:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # la columna ya existe
    conn.commit()
    return conn


def ajuste(conn: sqlite3.Connection, clave: str, valor: str | None = None) -> str | None:
    """Lee o escribe un ajuste suelto (por ejemplo el offset de Telegram)."""
    if valor is None:
        row = conn.execute("SELECT valor FROM ajustes WHERE clave=?", (clave,)).fetchone()
        return row["valor"] if row else None
    conn.execute("INSERT INTO ajustes (clave,valor) VALUES (?,?)"
                 " ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (clave, valor))
    conn.commit()
    return valor


def guardar_notion_page(conn: sqlite3.Connection, uid: str, page_id: str) -> None:
    conn.execute("UPDATE jobs SET notion_page=? WHERE uid=?", (page_id, uid))
    conn.commit()


def buscar(conn: sqlite3.Connection, uid: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM jobs WHERE uid=?", (uid,)).fetchone()


def new_jobs(conn: sqlite3.Connection, jobs: list[dict]) -> list[dict]:
    """Inserta las que no existan y devuelve solo esas."""
    fresh = []
    for job in jobs:
        job["uid"] = uid(job)
        cur = conn.execute(
            "INSERT OR IGNORE INTO jobs"
            " (uid,title,company,location,url,source,score,posted,email)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (job["uid"], job["title"], job.get("company"), job.get("location"),
             job.get("url"), job.get("source"), job.get("score", 0),
             job.get("posted"), job.get("email")),
        )
        if cur.rowcount:
            fresh.append(job)
    conn.commit()
    return fresh


def mark_notified(conn: sqlite3.Connection, jobs: list[dict]) -> None:
    conn.executemany("UPDATE jobs SET notified=1 WHERE uid=?", [(j["uid"],) for j in jobs])
    conn.commit()


TOLERANCIA = 4  # palabras de diferencia que no merecen un aviso


def page_changed(conn: sqlite3.Connection, url: str, name: str, texto: str) -> bool:
    """True si la pagina de empleo de un partner ha cambiado de verdad.

    Comparar hashes hacia saltar la alarma por una sola palabra distinta, y
    muchas webs rotan testimonios, noticias o un contador. Se guarda el texto
    normalizado y se exige que el vocabulario cambie en mas de TOLERANCIA
    palabras: una oferta nueva mueve decenas, un carrusel mueve dos.
    """
    row = conn.execute("SELECT texto FROM watch WHERE url=?", (url,)).fetchone()
    conn.execute(
        "INSERT INTO watch (url,name,digest,texto) VALUES (?,?,?,?)"
        " ON CONFLICT(url) DO UPDATE SET texto=excluded.texto,"
        " digest=excluded.digest, checked_at=CURRENT_TIMESTAMP",
        (url, name, hashlib.sha1(texto.encode("utf-8")).hexdigest(), texto),
    )
    conn.commit()

    if row is None or not row["texto"]:
        return False  # primera vez: solo memorizar, nunca avisar

    antes, ahora = set(row["texto"].split()), set(texto.split())
    return len(antes ^ ahora) > TOLERANCIA
