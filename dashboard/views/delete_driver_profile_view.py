                                               

from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from hire.models.driver_profile import DriverProfile                                 

@method_decorator(login_required, name='dispatch')
class DeleteDriverProfileView(View):
    """
    View for deleting a DriverProfile instance.
    """
    def post(self, request, pk, *args, **kwargs):
        driver_profile = get_object_or_404(DriverProfile, pk=pk)
        profile_name = driver_profile.name                                       

        try:
            driver_profile.delete()
            messages.success(request, f"Driver Profile for '{profile_name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting driver profile for '{profile_name}': {e}")

        return redirect('dashboard:settings_driver_profiles')

