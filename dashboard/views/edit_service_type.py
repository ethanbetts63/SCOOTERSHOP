# SCOOTER_SHOP/dashboard/views/edit_service_type.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from service.models import ServiceType
from dashboard.forms import ServiceTypeForm

@user_passes_test(lambda u: u.is_staff)
def edit_service_type(request, pk):
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES, instance=service_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service type '{service_type.name}' updated successfully!")
            return redirect('dashboard:settings_service_types')
    else:
        form = ServiceTypeForm(instance=service_type)
    context = {
        'page_title': 'Edit Service Type',
        'form': form,
        'service_type': service_type,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/add_edit_service_type.html', context)