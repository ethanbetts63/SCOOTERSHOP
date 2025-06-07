from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from service.models import ServiceType

class ServiceTypeDeleteView(View):
    """
    Class-based view for deleting a specific service type.
    Handles POST requests for deletion.
    """

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests: deletes the ServiceType instance
        identified by the primary key (pk).
        """
        service_type = get_object_or_404(ServiceType, pk=pk)
        name = service_type.name # Get name before deletion for message
        try:
            service_type.delete()
            messages.success(request, f"Service type '{name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting service type: {e}")
        # Redirect back to the management page after deletion
        return redirect('service:service_types_management')

