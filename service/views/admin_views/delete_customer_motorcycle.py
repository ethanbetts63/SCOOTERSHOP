
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from service.models import CustomerMotorcycle # Ensure CustomerMotorcycle and ServiceProfile are imported


class CustomerMotorcycleDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Admin view for deleting a CustomerMotorcycle instance.
    Requires staff status to access.
    This view only handles POST requests for deletion.
    """
    def test_func(self):
        """
        Ensures that only staff members or superusers can access this view.
        """
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk, *args, **kwargs):
        """
        Handles POST requests to delete a CustomerMotorcycle.
        """
        motorcycle = get_object_or_404(CustomerMotorcycle, pk=pk)
        motorcycle_display_name = f"{motorcycle.year} {motorcycle.brand} {motorcycle.model}" # For success message
        motorcycle.delete()
        messages.success(request, f"Motorcycle '{motorcycle_display_name}' deleted successfully.")
        return redirect(reverse('service:admin_customer_motorcycles')) # Redirect back to the list view
