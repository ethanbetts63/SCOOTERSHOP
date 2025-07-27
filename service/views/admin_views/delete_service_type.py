from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.mixins import AdminRequiredMixin
from django.db.models import ProtectedError

from service.models import ServiceType


class ServiceTypeDeleteView(AdminRequiredMixin, View):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        service_type = get_object_or_404(ServiceType, pk=pk)
        service_type_name = service_type.name
        try:
            service_type.delete()
            messages.success(
                request, f"Service Type '{service_type_name}' deleted successfully."
            )
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete '{service_type_name}' because it is associated with existing service bookings.",
            )
        return redirect(reverse("service:service_types_management"))
