"""Descubre la pagina de empleo de cada partner de Odoo en Espana.

Los partners son pymes: no usan Greenhouse ni Lever, publican en su propia web.
Este script prueba las rutas habituales y escribe partners.json, que es lo que
luego vigila el radar.

    python descubrir_partners.py
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; radar-odoo/1.0)"}
TIMEOUT = 12

# Partners del directorio oficial (odoo.com/partners/country/spain-67) mas
# consultoras Odoo espanolas conocidas del ecosistema OCA.
CANDIDATOS = [
    ("QubiQ", "qubiq.es", "Barcelona"),
    ("Nanobytes", "nanobytes.es", "Barcelona/Madrid"),
    ("Studio73", "studio73.es", "Valencia/Madrid"),
    ("Indaws", "indaws.es", "Barcelona"),
    ("Tecnativa", "tecnativa.com", "Remoto"),
    ("Sygel Technology", "sygel.es", "Barcelona"),
    ("Landoo", "landoo.es", "Euskadi"),
    ("IPGRUP", "ipgrup.com", "Barcelona"),
    ("Comunitea", "comunitea.com", "Madrid"),
    ("Aselcis Consulting", "aselcis.com", "Madrid"),
    ("Domatix", "domatix.com", "Valencia"),
    ("FactorLibre", "factorlibre.com", "Madrid"),
    ("Guadaltech", "guadaltech.es", "Sevilla"),
    ("Trey", "trey.es", "Valencia"),
    ("Punt Sistemes", "puntsistemes.com", "Valencia"),
    ("Dynapps", "dynapps.eu", "Barcelona"),
    ("Octupus", "octupus.es", "Madrid"),
    ("Zeumat", "zeumat.com", "Barcelona"),
    ("Kernet", "kernet.es", "Bizkaia"),
    ("Acysos", "acysos.com", "Zaragoza"),
    ("Moldeo Interactive", "moldeo.io", "Barcelona"),
    ("Solvos", "solvos.es", "Asturias"),
]

RUTAS = [
    "/empleo", "/empleo/", "/trabaja-con-nosotros", "/trabaja-con-nosotros/",
    "/careers", "/careers/", "/jobs", "/jobs/", "/unete", "/talento",
    "/es/empleo", "/quienes-somos/empleo", "/work-with-us", "/rrhh",
]

PISTAS = ("empleo", "vacante", "ofertas de trabajo", "trabaja con nosotros",
          "careers", "join us", "unete a", "seleccion de personal", "hiring")

CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Direcciones que no sirven para escribir a una persona.
RUIDO = ("no-reply", "noreply", "example.com", "sentry", "wixpress", "@2x",
         ".png", ".jpg", ".gif", "domain.com", "tu-email", "your-email",
         "email@", "@sentry", "abuse@", "postmaster@")

# Prefijos que suelen llevar a quien decide, ordenados de mejor a peor.
PRIORIDAD = ("rrhh", "empleo", "talento", "jobs", "career", "consultor",
             "odoo", "hola", "contacto", "info")


def correos(html: str) -> list[str]:
    """Saca las direcciones utiles de una pagina, las mejores primero."""
    vistos = {m.lower() for m in CORREO.findall(html)}
    utiles = [m for m in vistos
              if len(m) < 60 and not any(r in m for r in RUIDO)]

    def rango(direccion: str) -> tuple[int, str]:
        local = direccion.split("@")[0]
        for i, p in enumerate(PRIORIDAD):
            if p in local:
                return (i, direccion)
        return (len(PRIORIDAD), direccion)  # personas con nombre propio al final

    return [d for _, d in sorted(rango(d) for d in utiles)][:4]


def probar(nombre: str, dominio: str, ciudad: str) -> dict | None:
    base = f"https://{dominio}"
    try:
        home = requests.get(base, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        home.raise_for_status()
    except requests.RequestException as exc:
        return {"name": nombre, "city": ciudad, "web": base, "careers": None,
                "error": type(exc).__name__}

    careers, via = None, "solo-home"

    # 1) Un enlace de la home que huela a empleo.
    for href, texto in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.{0,80}?)</a>',
                                  home.text, re.S | re.I):
        blob = (href + " " + texto).lower()
        if any(p in blob for p in PISTAS):
            careers = href if href.startswith("http") else base + "/" + href.lstrip("/")
            via = "enlace-home"
            break

    # 2) Si no, las rutas habituales.
    if not careers:
        for ruta in RUTAS:
            try:
                r = requests.get(base + ruta, headers=UA, timeout=TIMEOUT)
            except requests.RequestException:
                continue
            if r.status_code == 200 and any(p in r.text.lower() for p in PISTAS):
                careers, via = base + ruta, "ruta"
                break

    # Los correos utiles suelen estar en la pagina de empleo, no en la home:
    # hay que abrirla siempre, tambien cuando se llego a ella por un enlace.
    paginas = [home.text]
    if careers:
        try:
            paginas.append(requests.get(careers, headers=UA, timeout=TIMEOUT).text)
        except requests.RequestException:
            pass

    encontrados: list[str] = []
    for pagina in reversed(paginas):          # la de empleo manda sobre la home
        for direccion in correos(pagina):
            if direccion not in encontrados:
                encontrados.append(direccion)

    return {"name": nombre, "city": ciudad, "web": base, "careers": careers,
            "emails": encontrados[:4], "via": via}


def main() -> None:
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(lambda c: probar(*c), CANDIDATOS))

    vivos = [r for r in resultados if not r.get("error")]
    Path("partners.json").write_text(
        json.dumps(vivos, ensure_ascii=False, indent=2), encoding="utf-8")

    for r in resultados:
        estado = r.get("error") or (r["careers"] or "(solo home)")
        correo = (r.get("emails") or ["-"])[0]
        print(f"{r['name']:<22} {correo:<28} {estado}")
    print(f"\n{len(vivos)}/{len(resultados)} partners guardados en partners.json")


if __name__ == "__main__":
    main()
