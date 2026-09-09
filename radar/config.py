"""Filtros y pesos del radar. Todo lo ajustable vive aqui.

Los pesos salen del CV real (Desktop\\moi\\cv-src\\content.py), no de intuicion:
Python + Odoo v15-v19, FastAPI/Flask/Django, PostgreSQL con tuning, Docker,
Linux, OCA, MRP e inventario, trazabilidad FEFO, GS1, APIs REST, ETL, n8n,
Selenium. 4 anos de experiencia. Ingles B1. Base en Terrassa (Barcelona).
"""

# Una oferta debe mencionar al menos una de estas para entrar siquiera.
KEYWORDS = [
    "odoo", "openerp", "erp",
    "python", "fastapi", "flask", "django",
]

# Peso por tecnologia. Cuanto mas encaje con el CV, mas arriba sale.
BOOST = {
    # Nucleo Odoo: es donde tiene 4 anos y donde menos competencia hay
    "odoo": 50, "openerp": 40, "oca": 25, "erp": 18,
    "mrp": 15, "trazabilidad": 12, "inventario": 10, "wms": 10,
    "gs1": 10, "datamatrix": 10, "fefo": 10, "xml-rpc": 12,

    # Python y frameworks del CV
    "python": 25, "fastapi": 22, "django": 16, "flask": 14,
    "api rest": 12, "rest api": 12, "apis rest": 12, "pcap": 10,

    # Datos
    "postgresql": 16, "postgres": 16, "mariadb": 8, "sqlite": 5, "sql": 5,

    # DevOps del CV
    "docker": 12, "docker compose": 8, "linux": 8, "git": 5, "ssh": 4,

    # Integraciones y automatizacion
    "etl": 12, "n8n": 12, "selenium": 10, "scraping": 10,
    "integracion": 6, "integración": 6, "automatizacion": 6, "automatización": 6,

    # Secundarias
    "node.js": 6, "nodejs": 6, "javascript": 5, "xml": 5,
    "pytest": 6, "pruebas unitarias": 6, "unit test": 5,

    # Geografia: vive en Terrassa
    "terrassa": 20, "barcelona": 15, "valles": 10, "sabadell": 8,
    "cataluña": 8, "catalunya": 8,

    # El idioma del anuncio ya dice algo del equipo
    "español": 5, "castellano": 5, "spanish": 4,
}

# Restan puntos: cosas que no encajan con el perfil real.
PENALIZA = {
    # Ingles B1: un puesto que exige nivel nativo no es realista hoy
    "native english": 25, "native-level english": 25, "fluent english": 15,
    "english c1": 12, "english c2": 15, "ingles c1": 12, "inglés c1": 12,

    # 4 anos de experiencia: ni becario ni director
    "becario": 12, "internship": 12, "unpaid": 30, "no remunerad": 30,
    "principal engineer": 15, "staff engineer": 15, "head of": 20,
    "engineering manager": 18, "cto": 20, "10+ years": 15, "12+ years": 20,

    # Sectores/condiciones que descartan de facto
    "security clearance": 40, "must relocate": 20,
}

# Ubicaciones validas. Se acepta una oferta si:
#   - es remota, o
#   - esta en Barcelona (presencial, hibrido o remoto), o
#   - esta en Madrid SOLO si es remota.
# Ojo: "hibrido" NO entra aqui. Un hibrido en Bruselas no sirve; solo vale si
# ademas es de Barcelona, y de eso ya se encarga la lista BARCELONA.
REMOTE_HINTS = ["remote", "remoto", "en remoto", "teletrabajo", "anywhere",
                "home office", "fully remote", "100% remoto"]
BARCELONA = ["barcelona", "bcn", "terrassa", "sabadell", "cataluna",
             "catalunya", "cataluña", "valles"]
MADRID = ["madrid"]
SPAIN = ["spain", "espana", "españa"]

# Descartan la oferta aunque diga "remote": el remoto de EE.UU. no sirve.
BLOCK = [
    "only in usa", "us only", "us-only", "united states only", "canada only",
    "latam only", "remote (us", "remote - us", "us based", "u.s. based",
    "must be located in the united states", "must reside in the us",
    "authorized to work in the us", "green card", "usc only",
    "americas only", "apac only", "india only", "philippines only",
]

# Si el titulo lleva otra tecnologia principal, la oferta no es para el, aunque
# el cuerpo mencione Python de pasada. Un "Senior Rust Engineer" que usa Docker
# y Postgres puntuaba 102 antes de esto.
TITULO_VETO = [
    "rust", "ruby", "rails", "java ", "java,", "java/", "kotlin", "scala",
    "php", "golang", " go ", ".net", "c#", "c++", "elixir", "perl",
    "salesforce", "sap ", "abap", "sharepoint", "wordpress",
    "frontend", "front-end", "react", "angular", "vue",
    "android", "ios ", "swift", "unity",
    "sales", "account executive", "marketing", "designer", "recruiter",
    "support specialist", "customer success", "project manager",
]

# Si el titulo dice esto, el veto no aplica: es su terreno.
TITULO_SALVA = ["odoo", "python", "fastapi", "django", "flask", "erp"]

# Por debajo de esto no molesta. Bajarlo = mas ofertas y mas ruido.
MIN_SCORE = 40

# Tope de avisos por ejecucion, para no recibir un muro en Telegram.
MAX_AVISOS = 15

PARTNERS_FILE = "partners.json"
