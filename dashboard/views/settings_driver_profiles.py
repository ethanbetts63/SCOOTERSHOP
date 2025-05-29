# dashboard/views/settings_driver_profiles.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from hire.models.driver_profile import DriverProfile # Import the DriverProfile model

@method_decorator(login_required, name='dispatch')
class DriverProfilesSettingsView(View):
    """
    View for managing (listing, searching) driver profiles.
    """
    template_name = 'dashboard/settings_driver_profiles.html'

    def get(self, request, *args, **kwargs):
        # Fetch all driver profiles, ordered by name and email
        driver_profiles = DriverProfile.objects.all().order_by('name', 'email')

        context = {
            'driver_profiles': driver_profiles
        }
        return render(request, self.template_name, context)

