import os
import django
from django.conf import settings

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SCOOTER_SHOP.settings')
django.setup()

from core.sitemaps import CoreSitemap
from inventory.sitemaps import InventorySitemap, MotorcycleSitemap
from service.sitemaps import ServiceSitemap
from django.urls import reverse

print("Starting sitemap generation test...")

sitemaps = {
    'core': CoreSitemap,
    'inventory': InventorySitemap,
    'motorcycles': MotorcycleSitemap,
    'service': ServiceSitemap,
}

for section, sitemap_class in sitemaps.items():
    try:
        print(f"--- Processing section: {section} ---")
        sitemap_instance = sitemap_class()
        items_list = list(sitemap_instance.items())
        print(f"Found {len(items_list)} items in section '{section}'")

        # Check a few items for URL generation
        for i, item in enumerate(items_list):
            if i > 5: # Limit checks to first 5 items per section for speed
                break
            url = sitemap_instance.location(item)
            if not url:
                print(f"WARNING: No URL generated for item: {item}")

        print(f"--- Section '{section}' processed successfully ---")
    except Exception as e:
        print(f"!!! ERROR in section '{section}' !!!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e}")
        # Re-raising the exception to get a full traceback
        raise

print("\nSitemap generation test finished.")
