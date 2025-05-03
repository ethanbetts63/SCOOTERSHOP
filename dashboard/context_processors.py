# dashboard/context_processors.py

# Import the SiteSettings model from the dashboard app
from .models import SiteSettings
from django.conf import settings # Import settings if needed

# Context processor to add SiteSettings to the context of every request.
# This function needs to be listed in the 'context_processors' setting in your project's settings.py
def site_settings(request):
    try:
        # Attempt to get the SiteSettings instance using the static method
        settings_object = SiteSettings.get_settings()
    except Exception:
        # Handle cases where SiteSettings might not exist yet (e.g., before initial data is created)
        # or if there's an error fetching it.
        settings_object = None
        # Log the error in a real application
        # import logging
        # logging.exception("Error fetching SiteSettings in context processor")

    # Return a dictionary where the key is the variable name in templates
    return {'settings': settings_object}