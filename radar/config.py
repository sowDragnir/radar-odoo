"""Filtros y fuentes del radar. Todo lo ajustable vive aqui."""

# Una oferta debe mencionar al menos una de estas para entrar.
KEYWORDS = [
    "odoo", "openerp", "owl framework", "xml-rpc",
    "python", "django", "flask", "fastapi",
]

# Peso extra: cuanto mas encaje con el perfil, mas arriba sale.
BOOST = {
    "odoo": 50, "openerp": 40, "erp": 15, "xml-rpc": 15, "owl": 10,
    "python": 20, "postgresql": 10, "docker": 5, "django": 5,
    "junior": 8, "backend": 5,
}

# Ubicaciones validas. El radar acepta una oferta si:
#   - es remota, o
#   - esta en Barcelona (presencial, hibrido o remoto), o
#   - esta en Madrid SOLO si es remota.
REMOTE_HINTS = ["remote", "remoto", "en remoto", "teletrabajo", "anywhere", "home office"]
BARCELONA = ["barcelona", "bcn", "cataluna", "catalunya", "cataluña"]
MADRID = ["madrid"]
SPAIN = ["spain", "espana", "españa", "es"]

# Descartan la oferta aunque diga "remote": el remoto de EE.UU. no te sirve.
BLOCK = [
    "only in usa", "us only", "us-only", "united states only", "canada only",
    "latam only", "remote (us", "remote - us", "us based", "u.s. based",
    "must be located in the united states", "must reside in the us",
    "authorized to work in the us", "green card", "usc only",
    "americas only", "apac only", "india only", "philippines only",
]

# Por debajo de esto no molesta. Subirlo = menos ruido, mas riesgo de perderse algo.
MIN_SCORE = 35

# Tope de avisos por ejecucion, para no recibir un muro en Telegram.
MAX_AVISOS = 15

# Partners oficiales de Odoo en Espana (odoo.com/partners/country/spain-67).
# 'careers' se rellena con descubrir_paginas.py; si esta vacio se vigila la home.
PARTNERS_FILE = "partners.json"
