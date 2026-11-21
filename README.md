# NOVA MARKET

Premium full-stack e-commerce application built for the CodeAlpha Full Stack Development Internship.

## Features

- Responsive Django storefront with product search, filtering, sorting, pagination, stock visibility, discounts, and image galleries.
- Django authentication, customer profiles, secure logout, and password changes.
- Guest session carts and authenticated database carts with safe merging.
- Transactional Cash on Delivery checkout with server-side pricing, delivery fees, stock locking, idempotency, and inventory movements.
- Order history, detail pages, cancellation, and exact-once stock restoration.
- Product and inventory administration through Django Admin.
- Versioned REST API at `/api/v1/` with session authentication.
- Swagger UI, OpenAPI schema, and ReDoc documentation.
- Health endpoint at `/health/`.

## Technology

Python 3.11+, Django 5.2, Django REST Framework, drf-spectacular, PostgreSQL in production, SQLite for local development, Pillow, WhiteNoise, Gunicorn, and vanilla HTML/CSS/JavaScript.

## Architecture

```text
config/       Settings, URLs, WSGI/ASGI
store/        Products, categories, images, inventory, catalogue, product API
accounts/     Authentication, profiles, account API
cart/         Guest/authenticated carts and shared cart services
orders/       Checkout, orders, cancellation, email, order API
templates/    Server-rendered pages
static/       CSS and JavaScript
media/        Local development uploads
```

Cart and order rules are centralized in [cart/services.py](cart/services.py) and [orders/services.py](orders/services.py). HTML and API views reuse those services.

## Local installation

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_catalogue
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Environment variables

Copy [.env.example](.env.example) to `.env`. Never commit `.env`.

Production must provide:

- `DEBUG=False`
- A long random `SECRET_KEY`
- Explicit `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS` containing the HTTPS site origin
- PostgreSQL `DATABASE_URL`
- Secure cookie and HTTPS settings
- Persistent `MEDIA_ROOT` or object storage for uploads

Local development uses SQLite and non-secure HTTP cookies. Production settings automatically default to HTTPS redirects, secure cookies, and HSTS when `DEBUG=False`; deployment variables can override them explicitly.

## PostgreSQL

Set a connection string without committing credentials:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

Run migrations and checks:

```powershell
python manage.py migrate
python manage.py check --deploy
python manage.py test
```

Existing migrations include product, inventory, order payment, cancellation, and historical order snapshot changes. PostgreSQL concurrency testing is still required before claiming production-grade row-lock verification.

## Static files and media

WhiteNoise serves collected static files. Run:

```powershell
python manage.py collectstatic --noinput
```

Uploaded product images need persistent storage. The included Render blueprint mounts a persistent disk at `/var/data` and uses `/var/data/media`. On ephemeral platforms, configure S3-compatible object storage before accepting uploads.

## Deployment

Production startup command:

```text
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --access-logfile -
```

Build command:

```text
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Run migrations once in a release or pre-deploy step:

```text
python manage.py migrate
```

Do not run migrations from every worker startup. [render.yaml](render.yaml) provides a Render-compatible web service, PostgreSQL database, persistent media disk, health check, build command, pre-deploy migration, and Gunicorn startup. No live deployment URL is claimed because deployment has not been performed.

Docker support is provided by [Dockerfile](Dockerfile):

```powershell
docker build -t nova-market .
docker run --env-file .env -p 8000:8000 nova-market
```

## API documentation

- `/api/docs/` — Swagger UI
- `/api/schema/` — OpenAPI schema
- `/api/redoc/` — ReDoc

Main API groups:

- `/api/v1/products/` and `/api/v1/categories/`
- `/api/v1/auth/`
- `/api/v1/accounts/profile/`
- `/api/v1/cart/`
- `/api/v1/orders/`

Session-authenticated state-changing API requests require CSRF protection. Product and category reads are public; profiles and orders are user-scoped.

## Testing and release checks

```powershell
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate
python -m pip check
python manage.py test
```

The current isolated suite contains 41 passing tests covering authentication, permissions, catalogue, image validation, carts, checkout, rollback, idempotency, inventory, order ownership, API behavior, and CSRF boundaries.

## Security

- Production requires an explicit secret and allowed hosts.
- HTTPS redirect, secure cookies, HSTS, and content-type sniffing protection are configured through environment variables.
- Prices and totals are recalculated from database records.
- Checkout locks products and uses transactions.
- Profile and order access is user-scoped.
- API authentication endpoints are throttled.
- Product uploads validate extension, size, real image format, and file integrity.
- `.env`, database files, virtual environments, caches, logs, and uploaded media are excluded from Git.

## Known limitations

- PostgreSQL concurrency tests were not run locally; SQLite cannot provide equivalent row-locking verification.
- Online payments are intentionally not implemented; the application uses Cash on Delivery.
- Local media storage is unsuitable for ephemeral production platforms without persistent storage or object storage.
- No GitHub or live deployment URL is claimed until external publication is actually confirmed.

Phases 1–9 are implemented and validated. Phase 10 deployment preparation is complete locally; external publication requires GitHub and hosting credentials.
