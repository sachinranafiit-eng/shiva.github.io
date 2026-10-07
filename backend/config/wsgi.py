import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()

# Render free services do not expose a pre-deploy hook through the connected tool.
# On the single-instance service we run idempotent startup setup before serving.
if os.getenv('RUN_STARTUP_SETUP', 'false').lower() == 'true':
    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=1)
    call_command('seed_catalog', verbosity=1)
