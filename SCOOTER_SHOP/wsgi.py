# local version

import os
import sys
from django.core.wsgi import get_wsgi_application
project_home = '/home/ethanbetts/SCOOTER_SHOP'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SCOOTER_SHOP.settings")

application = get_wsgi_application()


# python anywhere version
import os
import sys
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

project_folder = os.path.expanduser('~/ScooterShop')
load_dotenv(os.path.join(project_folder, '.env'))

path = '/home/ethanbetts/ScooterShop'  
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SCOOTER_SHOP.settings')

application = get_wsgi_application()
