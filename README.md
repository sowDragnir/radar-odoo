# Radar Odoo

Radar de ofertas de **Python / Odoo** para España. Corre solo cada mañana en
GitHub Actions, avisa por **Telegram** y lleva el seguimiento en **Notion**.

No es un auto-apply. Manda avisos, no candidaturas: en un nicho de treinta
empresas, el volumen quema el nombre en lugar de abrir puertas.

## Por qué existe

Las herramientas de pago del sector prometen "aplicar a miles de ofertas", pero
todas beben de los mismos portales grandes. Los partners de Odoo en España son
pymes de 10-50 personas que **publican solo en su propia web**, y muchas montan
esa web con el módulo de RRHH del propio Odoo. Ese hueco es el que cubre esto.

Primera ejecución: encontró una vacante de Desarrollador/a Odoo 100% remota que
no estaba ni en LinkedIn ni en Indeed.

## Fuentes

| Fuente | Cómo | Cobertura |
|---|---|---|
| Partners de Odoo en España | `/jobs` del módulo de RRHH de Odoo, o hash de la página | España |
| Odoo S.A. | `odoo.com/jobs?country_id=67` | Barcelona |
| RemoteOK, Remotive, Arbeitnow, Jobicy | API pública JSON | Remoto |
| WeWorkRemotely | RSS | Remoto |
| Hacker News *Who is hiring?* | API de Algolia, filtrado a Europa | Remoto |

**LinkedIn queda fuera a propósito.** Su único acceso sin login es un endpoint
no documentado que se rompe cada pocas semanas, y scrapearlo pone en riesgo la
cuenta. Para LinkedIn: marcador con `f_TPR=r3600&sortBy=DD`.

## Filtro

Definido en `radar/config.py`:

- Barcelona en cualquier modalidad
- Madrid solo si es remoto
- Remoto general, descartando el remoto exclusivo de EE.UU.
- Puntuación por encaje (`odoo` en el título pesa mucho); umbral `MIN_SCORE`

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env          # rellenar tokens
python descubrir_partners.py  # genera partners.json
python -m radar.main --dry-run
```

## En GitHub Actions

Repo → Settings → Secrets and variables → Actions → *New repository secret*:

| Secret | De dónde sale |
|---|---|
| `TELEGRAM_TOKEN` | @BotFather |
| `TELEGRAM_CHAT_ID` | `api.telegram.org/bot<TOKEN>/getUpdates` |
| `NOTION_TOKEN` | notion.so/my-integrations (integración interna) |
| `NOTION_DB_ID` | el id de la URL de la base de datos |

El `.env` está en `.gitignore`. **Los tokens nunca van al repo.**

## Estructura

```
radar/
  config.py    filtros, pesos, umbral
  sources.py   una función por fuente
  match.py     puntuación y filtro geográfico
  store.py     SQLite: deduplicado y hashes de páginas
  notify.py    Telegram y Notion
  main.py      orquestación
descubrir_partners.py   genera partners.json
```

Una fuente caída no tumba el radar: se registra el fallo y sigue con las demás.
