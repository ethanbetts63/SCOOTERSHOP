# SCOOTER_SHOP/shop/context_processors.py

# Import models from your shop app
from .models import SiteSettings

# Context processor to add SiteSettings to the context of every request.
# This function needs to be listed in the 'context_processors' setting in your project's settings.py
def site_settings(request):
    try:
        # Attempt to get the SiteSettings instance
        settings = SiteSettings.get_settings() # Assuming get_settings() is a class method on SiteSettings
    except Exception:
        # Handle cases where SiteSettings might not exist yet (e.g., before initial data is created)
        settings = None
    # Return a dictionary where the key is the variable name in templates
    return {'settings': settings}