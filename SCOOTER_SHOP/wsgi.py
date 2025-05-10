"""
WSGI config for SCOOTER_SHOP project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application
project_home = '/home/ethanbetts/SCOOTER_SHOP'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SCOOTER_SHOP.settings")

application = get_wsgi_application()
