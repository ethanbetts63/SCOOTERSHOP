# SCOOTER_SHOP/dashboard/views/delete_service_brand.py

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from service.models import ServiceBrand

@user_passes_test(lambda u: u.is_staff)
def delete_service_brand(request, pk):
    if request.method != 'POST':
        messages.error(request, "Invalid request method. Please use the form to delete brands.")
        return redirect('dashboard:service_brands_management')

    try:
        brand_to_delete = get_object_or_404(ServiceBrand, pk=pk)
        brand_name = brand_to_delete.name
        brand_to_delete.delete()
        messages.success(request, f"Service brand '{brand_name}' deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting service brand: {e}")

    return redirect('dashboard:service_brands_management')