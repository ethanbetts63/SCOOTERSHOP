                                            

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from service.models import ServiceType                               

class ServiceTypeDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for deleting a ServiceType instance.
    Requires the user to be logged in and a staff member or superuser.
    """
    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests to delete a ServiceType.
        """
        service_type = get_object_or_404(ServiceType, pk=pk)
        service_type_name = service_type.name
        service_type.delete()
        messages.success(request, f"Service Type '{service_type_name}' deleted successfully.")
        return redirect(reverse('service:service_types_management'))

