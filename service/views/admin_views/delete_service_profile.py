

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import ServiceProfile

class ServiceProfileDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        profile = get_object_or_404(ServiceProfile, pk=pk)
        profile_name = profile.name # Store name before deletion for message
        profile.delete()
        messages.success(request, f"Service Profile for '{profile_name}' deleted successfully.")
        return redirect(reverse('service:admin_service_profiles'))

