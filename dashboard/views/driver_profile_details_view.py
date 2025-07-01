                                                

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from hire.models.driver_profile import DriverProfile

@method_decorator(login_required, name='dispatch')
class DriverProfileDetailView(View):
    """
    View for displaying detailed information about a single DriverProfile instance.
    Accessible only by administrators.
    """
    template_name = 'dashboard/driver_profile_details.html'

    def get(self, request, pk, *args, **kwargs):
        driver_profile = get_object_or_404(DriverProfile, pk=pk)
        context = {
            'driver_profile': driver_profile,
            'title': f"Driver Profile Details: {driver_profile.name or driver_profile.email}",
        }
        return render(request, self.template_name, context)

