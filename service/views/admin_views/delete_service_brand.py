from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from service.mixins import AdminRequiredMixin

from service.models import ServiceBrand


class ServiceBrandDeleteView(AdminRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):

        brand_to_delete = get_object_or_404(ServiceBrand, pk=pk)
        brand_name = brand_to_delete.name
        try:
            brand_to_delete.delete()
            messages.success(
                request, f"Service brand '{brand_name}' deleted successfully."
            )
        except Exception as e:
            messages.error(request, f"Error deleting service brand: {e}")

        return redirect("service:service_brands_management")
