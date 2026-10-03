# Shiva Enterprises service portal

The original Shiva Enterprises marketing site remains at the repository root. The React/TypeScript booking portal is in `frontend/` and publishes at `/shiva.github.io/portal/`. The Django REST API is in `backend/` and runs on a separate Python host. GitHub Pages serves static files only.

The deployment excludes the old `admin.html` and `admin.js`: they used a JavaScript PIN and browser storage, which cannot protect real bookings or inventory. Use authenticated Django admin at `https://YOUR_API_HOST/admin/` for staff management.

## Requirements and versions

- Python 3.11+ (tested on 3.11), Django 5.2.7, Django REST Framework 3.16.1, PostgreSQL via psycopg 3.2.10 in production.
- Node.js 22, pnpm 11.19.0, React 19.2.0, TypeScript 5.9.3, Vite 7.1.11.
- Python packages are pinned in `backend/requirements.txt`; frontend packages are in `frontend/package.json` and `frontend/pnpm-lock.yaml`.
- No SQL Server or ODBC dependency is used.

## Local setup — macOS / Linux

```bash
git clone https://github.com/sachinranafiit-eng/shiva.github.io.git
cd shiva.github.io
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set a unique `DJANGO_SECRET_KEY`. Export the values before starting Django:

```bash
set -a; source backend/.env; set +a
python backend/manage.py migrate
python backend/manage.py seed_catalog
python backend/manage.py createsuperuser
python backend/manage.py runserver 127.0.0.1:8000
```

In another terminal:

```bash
cd shiva.github.io/frontend
cp .env.example .env.local
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

Open the local URL printed by Vite (portal base `/shiva.github.io/portal/`).

## Local setup — Windows PowerShell

```powershell
git clone https://github.com/sachinranafiit-eng/shiva.github.io.git
cd shiva.github.io
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` and set a unique secret key. PowerShell does not automatically load `.env`:

```powershell
Get-Content backend\.env | Where-Object { $_ -match '^[^#=]+=' } | ForEach-Object { $name, $value = $_ -split '=', 2; [Environment]::SetEnvironmentVariable($name, $value, 'Process') }
python backend\manage.py migrate
python backend\manage.py seed_catalog
python backend\manage.py createsuperuser
python backend\manage.py runserver 127.0.0.1:8000
```

In another PowerShell terminal:

```powershell
cd shiva.github.io\frontend
Copy-Item .env.example .env.local
corepack enable
corepack prepare pnpm@11.19.0 --activate
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

Create technician accounts through Django admin: create a User, then a Profile with role `technician`. Staff accounts need Django `is_staff` and a staff Profile. Customers register in the portal. `seed_catalog` adds services and products, but no demo user credentials. It is safe to rerun; it does not overwrite stock or pricing edits.

The superuser account created by `createsuperuser` opens the **Shiva Enterprises Super Admin** at `/admin/`. It can manage all service rates, descriptions and photos; product details, photos and prices; time-bound fixed or percentage offers; service areas; availability slots and capacity; users and technician roles; addresses; bookings; invoices; and feedback. Stock counts and movement history are read-only there; receive or adjust stock through the authenticated stock API or operations dashboard so every change has a movement record. Offers reduce labour only, are checked when a customer books, and appear as a separate invoice discount. Changing a service price or offer later does not alter the booking's quoted starting rate or discount.

## API and roles

Swagger documentation: `http://127.0.0.1:8000/api/docs/`; OpenAPI JSON: `/api/schema/`. Endpoints cover registration/login/logout/profile, saved addresses, services, service areas, availability slots, offers, products, bookings, estimates, stock movements, job photos, invoices, feedback, technician directory and dashboard. Token authentication uses `Authorization: Token <token>`. The frontend keeps the token in session storage. Staff can publish timed slots with capacities; when a service has future slots, bookings are restricted to those slots and capacity is enforced transactionally. Services without published slots accept a preferred time as a request, subject to confirmation.

Customers see their own bookings and addresses. Technicians see assigned jobs only. Staff can assign jobs, manage catalog and stock, and use the Django admin. Estimate approval reserves material inside a database transaction; material issue lowers physical and reserved stock with a movement record. Booking and inventory changes write timestamped activity or stock movement records.

Service prices are starting amounts. The customer sees visit, labour, each material and tax separately. Customer-selected materials become a draft estimate; staff must send it for approval. A technician can also draft material recommendations after inspection. Cash is recorded by staff; `pay_after_service` remains unpaid until settled. No online payment success is simulated.

## GitHub Pages deployment

1. In repository **Settings → Pages**, select **GitHub Actions** as the source.
2. Deploy the Django API and PostgreSQL first. In **Settings → Secrets and variables → Actions → Variables**, set `PORTAL_API_URL` to the public HTTPS API base, for example `https://api.example.com/api`. This URL is public configuration, not a credential.
3. Push to `main` or run the **Deploy Shiva Enterprises site and portal** workflow manually. It builds the portal with base `/shiva.github.io/portal/`, copies the existing marketing site and assets, and deploys `_site`.
4. Verify `https://sachinranafiit-eng.github.io/shiva.github.io/` and `/shiva.github.io/portal/`. If `PORTAL_API_URL` is unset, the portal clearly reports that online booking is unavailable; it does not submit a fake booking.

## Android and iPhone installation

Open `https://sachinranafiit-eng.github.io/shiva.github.io/portal/?install=1` on the phone. The marketing site and portal both link to this page. The portal includes a web app manifest, Shiva icon and service worker scoped to `/shiva.github.io/portal/`.

- **Android:** Download the signed APK from `https://sachinranafiit-eng.github.io/shiva.github.io/downloads/shiva-enterprises-android.apk`, open it and follow Android's installation prompt. The APK is a WebView wrapper around the live portal. Chrome's **Install app** or **Add to Home screen** is also available for the website.
- **iPhone:** In Safari, tap **Share → Add to Home Screen**, enable **Open as Web App** if shown, then tap **Add**.

The Android source and `android/build-apk.sh` are included. Rebuild on macOS with Android SDK platform 35, Build Tools 36.1.0, Android Studio's JDK and `bash android/build-apk.sh`; the script signs and verifies `downloads/shiva-enterprises-android.apk`. It creates `.local-signing/shiva-release.jks` and `.local-signing/password` outside Git. **Back up both files privately:** future APK updates with the same package name must use the same key. Do not commit them. The APK is directly downloadable and not a Play Store listing. There is no IPA or App Store listing; iPhone uses the installed website. Store distribution needs the owner's developer accounts and review. The service worker caches the app shell and static assets; booking and material actions still require internet and the separately deployed API. It does not cache API responses or queue offline submissions.

## Production API and database

Deploy `backend/` to a Python-capable host with Python 3.11+, persistent PostgreSQL, HTTPS and persistent upload storage. Example start commands from the repository root:

```bash
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
gunicorn --chdir backend config.wsgi:application --bind 0.0.0.0:$PORT
```

Set `DJANGO_DEBUG=false`, a random `DJANGO_SECRET_KEY`, `DATABASE_URL=postgresql://...`, `DJANGO_ALLOWED_HOSTS=api.example.com`, `CORS_ALLOWED_ORIGINS=https://sachinranafiit-eng.github.io`, and `CSRF_TRUSTED_ORIGINS=https://api.example.com`. Terminate TLS at the host/proxy and forward `X-Forwarded-Proto: https`. Configure a durable `backend/media/` volume or replace Django's file storage with an object-storage backend before accepting production photos. Back up PostgreSQL and uploads.

For SMTP, set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL`. SMS/WhatsApp provider names and payment gateway settings are only configuration markers currently; no delivery or online charge is attempted. The API `/api/config/` reports what is configured. Until gateway integration and real credentials are provided, only cash and pay-after-service records are supported.

## Verification

```bash
cd shiva.github.io
source backend/.venv/bin/activate
set -a; source backend/.env; set +a
python backend/manage.py test portal.tests
cd frontend
pnpm build
```

The test suite covers customer and technician permissions, status transitions, estimate approval, stock shortage rollback, reservation, issue and purchase records.
