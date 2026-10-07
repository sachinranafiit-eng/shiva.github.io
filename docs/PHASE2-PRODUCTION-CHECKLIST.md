# Phase 2 production checklist

This repository is now prepared for a real customer booking flow, but the API still needs a production host and database before online accounts are enabled on GitHub Pages.

## Before deployment

- Review hosting cost before applying `render.yaml`; it intentionally declares paid resources.
- Keep `DEFAULT_TAX_RATE=0` until the business's accountant/tax adviser confirms the correct GST/tax treatment. Configure actual service/product rates in Django admin before billing.
- Create a unique production `DJANGO_SECRET_KEY`; never commit it.
- Use PostgreSQL in production and HTTPS only.
- Confirm `CORS_ALLOWED_ORIGINS=https://sachinranafiit-eng.github.io`.
- Create the production superuser using the host's secure shell, not in source code.
- Add actual technicians as users with Profile role `technician`.
- Review service areas, service rates, availability slots, stock and minimum stock before opening bookings.
- Customer/job photos require durable private storage before they should be relied on in production. Do not treat the Git repository as customer-file storage.

## Deployment sequence

1. Deploy Django + PostgreSQL and run migrations.
2. Run `python backend/manage.py seed_catalog`.
3. Run `python backend/manage.py createsuperuser` in the production shell.
4. Verify `/api/health/`, `/api/docs/`, registration, login and one complete test booking.
5. Set GitHub Actions variable `PORTAL_API_URL` to the HTTPS API base ending in `/api`.
6. Re-run **Deploy Shiva Enterprises site and portal**.
7. Test customer registration → address → booking → staff assignment → technician completion → invoice → feedback on the live portal.

## Controls added in Phase 2

- Authentication and booking rate limits.
- Required customer phone and email validation.
- Six-digit Indian PIN-code validation.
- Booking requests limited to 90 days ahead.
- Public database health check for hosting probes.
- Neutral default tax rate (0) instead of assuming 18%.
- Seed catalogue no longer creates competitor-comparison claims.
- GitHub CI runs Django checks, migrations check, backend tests and frontend build.
