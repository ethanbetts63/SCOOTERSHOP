# SCOOTER_SHOP/dashboard/views/delete_service_type.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from service.models import ServiceType

@user_passes_test(lambda u: u.is_staff)
def delete_service_type(request, pk):
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        name = service_type.name
        service_type.delete()
        messages.success(request, f"Service type '{name}' deleted successfully!")
        return redirect('dashboard:settings_service_types')
    context = {
        'page_title': 'Delete Service Type',
        'service_type': service_type
    }
    return render(request, 'dashboard/delete_service_type.html', context)