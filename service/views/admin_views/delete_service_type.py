from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from service.models import ServiceType


class ServiceTypeDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):

    def test_func(self):

        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):

        service_type = get_object_or_404(ServiceType, pk=pk)
        service_type_name = service_type.name
        service_type.delete()
        messages.success(
            request, f"Service Type '{service_type_name}' deleted successfully."
        )
        return redirect(reverse("service:service_types_management"))
