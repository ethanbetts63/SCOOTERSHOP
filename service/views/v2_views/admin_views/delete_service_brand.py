# SCOOTER_SHOP/service/views/admin_views.py (continued)

from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from service.models import ServiceBrand

class ServiceBrandDeleteView(View):
    """
    Class-based view for deleting a specific service brand.
    Handles POST requests for deletion.
    """
    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests: deletes the ServiceBrand instance
        identified by the primary key (pk).
        """
        brand_to_delete = get_object_or_404(ServiceBrand, pk=pk)
        brand_name = brand_to_delete.name # Get name before deletion for message
        try:
            brand_to_delete.delete()
            messages.success(request, f"Service brand '{brand_name}' deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting service brand: {e}")
        
        # Redirect back to the management page after deletion
        return redirect('service:service_brands_management')

