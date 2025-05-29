# dashboard/views/driver_profiles_settings_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from hire.models.driver_profile import DriverProfile

@method_decorator(login_required, name='dispatch')
class DriverProfilesSettingsView(View):
    """
    View for listing and managing DriverProfile instances.
    """
    template_name = 'dashboard/settings_driver_profiles.html'

    def get(self, request, *args, **kwargs):
        driver_profiles = DriverProfile.objects.all().order_by('name')
        context = {
            'driver_profiles': driver_profiles,
            'title': "Manage Driver Profiles",
        }
        return render(request, self.template_name, context)

@method_decorator(login_required, name='dispatch')
class DeleteDriverProfileView(View):
    """
    View for deleting a DriverProfile instance.
    """
    def post(self, request, pk, *args, **kwargs):
        driver_profile = get_object_or_404(DriverProfile, pk=pk)
        driver_profile_name = driver_profile.name # Store name before deletion
        driver_profile.delete()
        messages.success(request, f"Driver Profile for '{driver_profile_name}' deleted successfully!")
        return redirect('dashboard:settings_driver_profiles')

