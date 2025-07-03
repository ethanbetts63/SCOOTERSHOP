from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.mixins import AdminRequiredMixin
from service.models import CustomerMotorcycle


class CustomerMotorcycleDeleteView(AdminRequiredMixin, View):

    def test_func(self):

        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):

        motorcycle = get_object_or_404(CustomerMotorcycle, pk=pk)
        motorcycle_display_name = (
            f"{motorcycle.year} {motorcycle.brand} {motorcycle.model}"
        )
        motorcycle.delete()
        messages.success(
            request, f"Motorcycle '{motorcycle_display_name}' deleted successfully."
        )
        return redirect(reverse("service:admin_customer_motorcycle_management"))
